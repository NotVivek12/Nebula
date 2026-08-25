"""
Unit tests for SSRF protection utility.

Tests:
- Public URLs accepted
- localhost rejected
- 127.x.x.x rejected
- Private IP ranges rejected (10.x, 172.16-31.x, 192.168.x)
- Cloud metadata endpoint rejected (169.254.169.254)
- Non-HTTP scheme rejected (file://, ftp://)
- No hostname rejected
- DNS resolution to private IP rejected
"""

from unittest.mock import patch

import pytest

from app.utils.ssrf import SSRFError, validate_url, validate_webhook_url


class TestSSRFProtection:
    def test_public_https_url_accepted(self) -> None:
        url = validate_url("https://example.com/api")
        assert url == "https://example.com/api"

    def test_public_http_url_accepted(self) -> None:
        url = validate_url("http://example.com")
        assert url == "http://example.com"

    def test_localhost_rejected(self) -> None:
        with pytest.raises(SSRFError, match="blocked"):
            validate_url("http://localhost/admin")

    def test_127_loopback_rejected(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("http://127.0.0.1:8080/internal")

    def test_10_dot_private_rejected(self) -> None:
        # Patch DNS to avoid needing real network
        with patch("app.utils.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("10.0.0.1", 0))]
            with pytest.raises(SSRFError, match="blocked"):
                validate_url("http://internal.corp.example")

    def test_172_16_private_rejected(self) -> None:
        with patch("app.utils.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("172.20.0.5", 0))]
            with pytest.raises(SSRFError, match="blocked"):
                validate_url("http://internal.service")

    def test_192_168_private_rejected(self) -> None:
        with patch("app.utils.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("192.168.1.100", 0))]
            with pytest.raises(SSRFError, match="blocked"):
                validate_url("http://my-private-server")

    def test_cloud_metadata_ip_rejected(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_file_scheme_rejected(self) -> None:
        with pytest.raises(SSRFError, match="Scheme"):
            validate_url("file:///etc/passwd")

    def test_ftp_scheme_rejected(self) -> None:
        with pytest.raises(SSRFError, match="Scheme"):
            validate_url("ftp://files.example.com")

    def test_empty_url_rejected(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("")

    def test_none_rejected(self) -> None:
        with pytest.raises((SSRFError, TypeError)):
            validate_url(None)  # type: ignore

    def test_webhook_url_allows_custom_port(self) -> None:
        """Webhook URLs allow non-standard ports."""
        with patch("app.utils.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]
            url = validate_webhook_url("https://example.com:9000/webhook")
            assert "9000" in url

    def test_ssrf_via_dns_rebinding_rejected(self) -> None:
        """DNS resolution returning private IP should be rejected even for public hostname."""
        with patch("app.utils.ssrf.socket.getaddrinfo") as mock_dns:
            # DNS rebinding attack: hostname resolves to private IP
            mock_dns.return_value = [(None, None, None, None, ("192.168.0.1", 0))]
            with pytest.raises(SSRFError, match="blocked"):
                validate_url("http://attacker-controlled.example.com")
