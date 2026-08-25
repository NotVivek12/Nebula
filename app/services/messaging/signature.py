"""
WhatsApp webhook signature verification.

Meta sends an X-Hub-Signature-256 header with every webhook POST.
Value format: sha256=<hex_digest>

Verification uses HMAC-SHA256 with the App Secret as the key.
The comparison uses secrets.compare_digest to prevent timing attacks.

If WHATSAPP_APP_SECRET is not set, signature verification is skipped
in development only. In production this is a startup error (enforced by config).
"""

import hashlib
import hmac
import secrets

from app.core.config import settings
from app.core.logging import logger


def verify_whatsapp_signature(payload_bytes: bytes, signature_header: str | None) -> bool:
    """
    Verifies the Meta X-Hub-Signature-256 webhook signature.

    Args:
        payload_bytes: Raw request body bytes (must be the exact bytes Meta signed).
        signature_header: Value of X-Hub-Signature-256 header (e.g. "sha256=abc123...").

    Returns:
        True if signature is valid.
        False if signature is missing, malformed, or invalid.

    In development without an app secret, logs a warning and returns True
    so local testing is possible. In production, missing app secret is blocked
    at startup by config validation.
    """
    app_secret = settings.WHATSAPP_APP_SECRET

    if not app_secret:
        if settings.ENVIRONMENT == "production":
            # This should never happen — config validation blocks production startup
            # without an app secret. Fail safe.
            logger.error("CRITICAL: WhatsApp app secret missing in production — rejecting webhook")
            return False
        # Development convenience: allow without secret but log loudly
        logger.warning(
            "WHATSAPP_APP_SECRET not configured — skipping signature verification "
            "(only acceptable in development)"
        )
        return True

    if not signature_header:
        logger.warning("Webhook rejected: X-Hub-Signature-256 header missing")
        return False

    # Signature format: "sha256=<hex>"
    if not signature_header.startswith("sha256="):
        logger.warning("Webhook rejected: X-Hub-Signature-256 has unexpected format")
        return False

    received_hex = signature_header[len("sha256="):]

    # Compute expected signature
    expected = hmac.new(
        app_secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    valid = secrets.compare_digest(expected, received_hex)
    if not valid:
        logger.warning("Webhook rejected: X-Hub-Signature-256 mismatch")
    return valid
