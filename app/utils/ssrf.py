"""
SSRF (Server-Side Request Forgery) protection utilities.

Any feature that makes outbound HTTP requests on behalf of user-supplied URLs
MUST call validate_url() before making the request.

Blocked targets:
- localhost / 127.x.x.x
- Private IPv4 ranges (10.x, 172.16-31.x, 192.168.x)
- IPv6 loopback and link-local
- Cloud metadata endpoints (169.254.169.254, etc.)
- Any non-HTTP/HTTPS scheme
"""

import ipaddress
import socket
from urllib.parse import urlparse

# Explicitly blocked hostnames and IP patterns
_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
    }
)

_BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),         # Private
    ipaddress.ip_network("172.16.0.0/12"),       # Private
    ipaddress.ip_network("192.168.0.0/16"),      # Private
    ipaddress.ip_network("127.0.0.0/8"),         # Loopback
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local / cloud metadata
    ipaddress.ip_network("::1/128"),             # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),            # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),           # IPv6 link-local
    ipaddress.ip_network("0.0.0.0/8"),           # "This" network
    ipaddress.ip_network("100.64.0.0/10"),       # Carrier-grade NAT
]

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_ALLOWED_PORTS = frozenset({80, 443, 8080, 8443})  # default; extend if needed


class SSRFError(ValueError):
    """Raised when a URL fails SSRF validation."""


def _is_blocked_ip(ip_str: str) -> bool:
    """Returns True if the IP address falls within a blocked range."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _BLOCKED_IP_RANGES)
    except ValueError:
        return True  # unparseable → block by default


def validate_url(url: str, *, allow_any_port: bool = False) -> str:
    """
    Validates a URL is safe to request (no SSRF risk).

    - Only http:// and https:// schemes are allowed.
    - Hostname must not resolve to private/loopback/metadata IPs.
    - Performs DNS resolution to verify the resolved IP is public.

    Returns the validated URL on success.
    Raises SSRFError with a reason on failure.

    This function is synchronous by design (socket.getaddrinfo).
    Call from async code with asyncio.to_thread() if needed.
    """
    if not url or not isinstance(url, str):
        raise SSRFError("URL must be a non-empty string.")

    parsed = urlparse(url)

    # 1. Scheme check
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise SSRFError(
            f"Scheme '{parsed.scheme}' is not permitted. Only http and https are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL must have a valid hostname.")

    # 2. Direct hostname block
    if hostname.lower() in _BLOCKED_HOSTS:
        raise SSRFError(f"Hostname '{hostname}' is not permitted (blocked).")

    # 3. Check if hostname looks like an IP directly
    try:
        addr_direct = ipaddress.ip_address(hostname)
        if _is_blocked_ip(str(addr_direct)):
            raise SSRFError(f"IP address '{hostname}' is in a blocked range.")
    except ValueError:
        # Not a bare IP — continue to DNS resolution
        pass

    # 4. DNS resolution check
    try:
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            resolved_ip = info[4][0]
            if _is_blocked_ip(resolved_ip):
                raise SSRFError(
                    f"Hostname '{hostname}' resolves to a blocked IP: {resolved_ip}"
                )
    except SSRFError:
        raise
    except OSError as exc:
        raise SSRFError(f"Could not resolve hostname '{hostname}': {exc}") from exc

    # 5. Port check
    port = parsed.port
    if port is not None and not allow_any_port and port not in _ALLOWED_PORTS:
        raise SSRFError(
            f"Port {port} is not in the allowed port list. "
            "Contact your administrator to allowlist this port."
        )

    return url


def validate_webhook_url(url: str) -> str:
    """
    Validates a webhook/HTTP destination URL.

    Same as validate_url but allows common webhook ports.
    """
    return validate_url(url, allow_any_port=True)
