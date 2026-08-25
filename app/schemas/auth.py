from pydantic import BaseModel


class Token(BaseModel):
    """Schema for JWT access and refresh token responses."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    """Schema for requesting a new access token using a refresh token."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Schema for decoding JWT token contents."""

    sub: str | None = None
