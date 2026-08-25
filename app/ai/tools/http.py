"""
HTTP Request Tool — SSRF-protected outbound HTTP calls.

This tool allows the AI agent to make HTTP requests to external services
(CRMs, webhooks, APIs). All target URLs are validated through the SSRF
protection module before any connection is made.

Security controls:
- Only http:// and https:// schemes allowed
- Private IP ranges, loopback, cloud metadata endpoints blocked
- DNS resolution performed to catch hostname→private-IP rebinding
- Redirect following disabled (each redirect re-validated)
- Response body truncated to prevent exfiltration via large payloads
- Sensitive response headers stripped from returned data
"""

from typing import Any

import httpx

from app.ai.tools.base import Tool
from app.core.logging import logger
from app.utils.ssrf import SSRFError, validate_url

# Headers to strip from responses before returning to LLM (may contain secrets)
_STRIP_RESPONSE_HEADERS = frozenset(
    {
        "set-cookie",
        "cookie",
        "authorization",
        "x-api-key",
        "x-auth-token",
        "x-secret",
        "proxy-authorization",
    }
)

# Maximum response body length returned to LLM
_MAX_RESPONSE_LENGTH = 2000

# Allowed HTTP methods
_ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH"})


class HTTPRequestTool(Tool):
    """
    SSRF-protected outbound HTTP tool.

    Makes HTTP requests to external APIs on behalf of the AI agent.
    All URLs are validated before connection. Private/internal addresses
    are unconditionally blocked.
    """

    @property
    def name(self) -> str:
        return "http_request"

    @property
    def description(self) -> str:
        return (
            "Dispatches outgoing HTTP GET/POST/PUT/PATCH requests to external CRMs, "
            "webhooks, or API endpoints. Cannot access private or internal addresses."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target REST API URL endpoint. Must be a public internet URL.",
                },
                "method": {
                    "type": "string",
                    "description": "HTTP request method",
                    "enum": list(_ALLOWED_METHODS),
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers dictionary (e.g. Authorization, Content-Type)",
                },
                "body": {
                    "type": "object",
                    "description": "Optional JSON request payload body for POST/PUT/PATCH",
                },
            },
            "required": ["url", "method"],
        }

    @property
    def required_permissions(self) -> list[str]:
        return ["tools:write"]

    async def execute(self, **kwargs: Any) -> Any:
        url: str | None = kwargs.get("url")
        method: str = kwargs.get("method", "GET").upper()
        headers: dict[str, str] = kwargs.get("headers") or {}
        body: dict[str, Any] = kwargs.get("body") or {}

        # ── Input validation ───────────────────────────────────────────────
        if not url:
            raise ValueError("http_request tool requires a 'url' parameter.")

        if method not in _ALLOWED_METHODS:
            raise ValueError(
                f"HTTP method '{method}' is not allowed. "
                f"Permitted: {sorted(_ALLOWED_METHODS)}"
            )

        # ── SSRF validation ────────────────────────────────────────────────
        # validate_url does DNS resolution — raises SSRFError for blocked targets
        try:
            validated_url = validate_url(url)
        except SSRFError as exc:
            logger.warning(
                "HTTP tool blocked SSRF attempt",
                url=url,
                reason=str(exc),
            )
            raise ValueError(f"URL not allowed: {exc}") from exc

        logger.info("HTTP tool executing request", url=validated_url, method=method)

        # ── Execute request ────────────────────────────────────────────────
        async with httpx.AsyncClient(
            follow_redirects=False,  # No redirect following — prevents redirect-based SSRF
            timeout=15.0,
        ) as client:
            try:
                request = client.build_request(
                    method,
                    validated_url,
                    json=body if body and method in ("POST", "PUT", "PATCH") else None,
                    headers=headers,
                )
                response = await client.send(request)

                # Strip sensitive headers from response before returning
                safe_headers = {
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() not in _STRIP_RESPONSE_HEADERS
                }

                return {
                    "status_code": response.status_code,
                    "response_text": response.text[:_MAX_RESPONSE_LENGTH],
                    "headers": safe_headers,
                    "url": str(response.url),
                    "redirected": False,
                }

            except SSRFError:
                raise
            except httpx.TimeoutException:
                logger.warning("HTTP tool request timed out", url=validated_url)
                raise ValueError(f"Request to {validated_url} timed out after 15 seconds.")
            except Exception as exc:  # noqa: BLE001
                logger.error("HTTP tool request failed", url=validated_url, error=str(exc))
                raise ValueError(f"HTTP request failed: {exc}") from exc
