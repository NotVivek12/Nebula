"""
Unit tests for security utilities.

Tests:
- Password hashing and verification
- Password strength validation
- JWT access token creation and decoding
- Token type enforcement (refresh tokens rejected as access)
- Refresh token hashing
"""

from datetime import timedelta

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    get_password_hash,
    hash_refresh_token,
    validate_password_strength,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self) -> None:
        hashed = get_password_hash("mypassword123A")
        assert hashed != "mypassword123A"
        assert len(hashed) > 20

    def test_verify_correct_password(self) -> None:
        hashed = get_password_hash("CorrectHorse99")
        assert verify_password("CorrectHorse99", hashed) is True

    def test_reject_wrong_password(self) -> None:
        hashed = get_password_hash("CorrectHorse99")
        assert verify_password("WrongHorse99", hashed) is False

    def test_hash_is_different_each_time(self) -> None:
        h1 = get_password_hash("SamePassword1")
        h2 = get_password_hash("SamePassword1")
        # bcrypt uses different salts
        assert h1 != h2

    def test_verify_empty_password_returns_false(self) -> None:
        hashed = get_password_hash("ValidPass1")
        assert verify_password("", hashed) is False


class TestPasswordStrength:
    def test_rejects_short_password(self) -> None:
        ok, msg = validate_password_strength("Ab1")
        assert ok is False
        assert "8" in msg

    def test_rejects_no_uppercase(self) -> None:
        ok, msg = validate_password_strength("lowercase123")
        assert ok is False
        assert "uppercase" in msg.lower()

    def test_rejects_no_lowercase(self) -> None:
        ok, msg = validate_password_strength("UPPERCASE123")
        assert ok is False
        assert "lowercase" in msg.lower()

    def test_rejects_no_digit(self) -> None:
        ok, msg = validate_password_strength("NoDigitsHere")
        assert ok is False
        assert "digit" in msg.lower()

    def test_accepts_valid_password(self) -> None:
        ok, msg = validate_password_strength("ValidPass123")
        assert ok is True
        assert msg == ""


class TestJWT:
    def test_create_and_decode_token(self) -> None:
        user_id = "user-123"
        token = create_access_token(subject=user_id)
        decoded = decode_access_token(token)
        assert decoded == user_id

    def test_expired_token_returns_none(self) -> None:
        token = create_access_token(subject="user-1", expires_delta=timedelta(seconds=-1))
        result = decode_access_token(token)
        assert result is None

    def test_garbage_token_returns_none(self) -> None:
        result = decode_access_token("not.a.token")
        assert result is None

    def test_token_includes_required_claims(self) -> None:
        import jwt

        from app.core.config import settings

        token = create_access_token(subject="user-abc")
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        assert payload["sub"] == "user-abc"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "iss" in payload
        assert "aud" in payload


class TestRefreshTokenHashing:
    def test_raw_and_hashed_differ(self) -> None:
        raw, hashed = generate_refresh_token()
        assert raw != hashed
        assert len(raw) > 20
        assert len(hashed) == 64  # SHA-256 hex = 64 chars

    def test_same_raw_produces_same_hash(self) -> None:
        raw = "deterministic_value"
        h1 = hash_refresh_token(raw)
        h2 = hash_refresh_token(raw)
        assert h1 == h2

    def test_different_raws_produce_different_hashes(self) -> None:
        h1 = hash_refresh_token("value_a")
        h2 = hash_refresh_token("value_b")
        assert h1 != h2
