"""
Unit tests for WhatsApp webhook signature verification.

Tests:
- Valid signature accepted
- Missing signature header rejected
- Tampered payload rejected
- Wrong format rejected
- Development mode without secret (permissive)
"""

import hashlib
import hmac
import json
from unittest.mock import patch

from app.services.messaging.signature import verify_whatsapp_signature

APP_SECRET = "test_app_secret_for_hmac_testing"
PAYLOAD = json.dumps({"object": "whatsapp_business_account", "entry": []}).encode()


def _make_signature(payload: bytes, secret: str = APP_SECRET) -> str:
    """Computes valid Meta X-Hub-Signature-256 header value."""
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestWebhookSignatureVerification:
    def test_valid_signature_accepted(self) -> None:
        sig = _make_signature(PAYLOAD)
        with patch("app.services.messaging.signature.settings") as mock_settings:
            mock_settings.WHATSAPP_APP_SECRET = APP_SECRET
            mock_settings.ENVIRONMENT = "production"
            result = verify_whatsapp_signature(PAYLOAD, sig)
        assert result is True

    def test_missing_header_rejected(self) -> None:
        with patch("app.services.messaging.signature.settings") as mock_settings:
            mock_settings.WHATSAPP_APP_SECRET = APP_SECRET
            mock_settings.ENVIRONMENT = "production"
            result = verify_whatsapp_signature(PAYLOAD, None)
        assert result is False

    def test_wrong_signature_rejected(self) -> None:
        bad_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        with patch("app.services.messaging.signature.settings") as mock_settings:
            mock_settings.WHATSAPP_APP_SECRET = APP_SECRET
            mock_settings.ENVIRONMENT = "production"
            result = verify_whatsapp_signature(PAYLOAD, bad_sig)
        assert result is False

    def test_tampered_payload_rejected(self) -> None:
        sig = _make_signature(PAYLOAD)
        tampered = PAYLOAD + b"extra"
        with patch("app.services.messaging.signature.settings") as mock_settings:
            mock_settings.WHATSAPP_APP_SECRET = APP_SECRET
            mock_settings.ENVIRONMENT = "production"
            result = verify_whatsapp_signature(tampered, sig)
        assert result is False

    def test_malformed_header_format_rejected(self) -> None:
        with patch("app.services.messaging.signature.settings") as mock_settings:
            mock_settings.WHATSAPP_APP_SECRET = APP_SECRET
            mock_settings.ENVIRONMENT = "production"
            # Missing "sha256=" prefix
            result = verify_whatsapp_signature(PAYLOAD, "invalid_format_no_prefix")
        assert result is False

    def test_development_without_secret_returns_true(self) -> None:
        """In development, missing app secret allows through with a warning."""
        with patch("app.services.messaging.signature.settings") as mock_settings:
            mock_settings.WHATSAPP_APP_SECRET = ""
            mock_settings.ENVIRONMENT = "development"
            result = verify_whatsapp_signature(PAYLOAD, None)
        assert result is True

    def test_production_without_secret_returns_false(self) -> None:
        """In production, missing app secret is a hard failure."""
        with patch("app.services.messaging.signature.settings") as mock_settings:
            mock_settings.WHATSAPP_APP_SECRET = ""
            mock_settings.ENVIRONMENT = "production"
            result = verify_whatsapp_signature(PAYLOAD, None)
        assert result is False

    def test_timing_safe_comparison(self) -> None:
        """Verify we use secrets.compare_digest (constant-time) not ==."""
        import inspect

        import app.services.messaging.signature as sig_module

        source = inspect.getsource(sig_module)
        assert "compare_digest" in source, (
            "Signature comparison MUST use secrets.compare_digest to prevent timing attacks"
        )
