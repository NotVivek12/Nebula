"""
Application configuration.

All settings are loaded from environment variables (or .env file for development).
No insecure defaults are permitted in production.
"""

from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ──────────────────────────────────────────────────────────────
    # General
    # ──────────────────────────────────────────────────────────────
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    PROJECT_NAME: str = "Nebula"
    API_V1_STR: str = "/api/v1"

    # ──────────────────────────────────────────────────────────────
    # Security / JWT
    # ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change_this_to_a_secure_random_key_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "nebula"
    JWT_AUDIENCE: str = "nebula-api"

    # ──────────────────────────────────────────────────────────────
    # CORS
    # Comma-separated list of allowed origins, e.g.:
    #   CORS_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
    # Use "*" only in development.
    # ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        """Returns CORS origins as a parsed list."""
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ──────────────────────────────────────────────────────────────
    # PostgreSQL
    # ──────────────────────────────────────────────────────────────
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "nebula"

    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ──────────────────────────────────────────────────────────────
    # Redis
    # ──────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ──────────────────────────────────────────────────────────────
    # Celery (uses same Redis by default)
    # ──────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    @property
    def effective_celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def effective_celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    # ──────────────────────────────────────────────────────────────
    # Qdrant
    # ──────────────────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "nebula_knowledge"

    @property
    def QDRANT_URL(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # ──────────────────────────────────────────────────────────────
    # WhatsApp / Meta
    # ──────────────────────────────────────────────────────────────
    WHATSAPP_VERIFY_TOKEN: str = "nebula_verify_token"
    # The App Secret from Meta Developer Console – used to verify webhook signatures.
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_API_VERSION: str = "v20.0"

    # ──────────────────────────────────────────────────────────────
    # AI Providers
    # ──────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Default AI provider for new tenants
    DEFAULT_AI_PROVIDER: str = "nvidia"
    DEFAULT_AI_MODEL: str = "nvidia/llama-3.1-nemotron-70b-instruct"

    # ──────────────────────────────────────────────────────────────
    # Object Storage (S3-compatible)
    # ──────────────────────────────────────────────────────────────
    OBJECT_STORAGE_ENDPOINT: str = ""
    OBJECT_STORAGE_ACCESS_KEY: str = ""
    OBJECT_STORAGE_SECRET_KEY: str = ""
    OBJECT_STORAGE_BUCKET: str = "nebula-media"
    OBJECT_STORAGE_REGION: str = "us-east-1"

    # ──────────────────────────────────────────────────────────────
    # Logging
    # ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "info"
    JSON_LOGS: bool = False

    # ──────────────────────────────────────────────────────────────
    # Rate limiting defaults
    # ──────────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ──────────────────────────────────────────────────────────────
    # Production safety guard
    # ──────────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Refuse to start in production if unsafe defaults remain."""
        if self.ENVIRONMENT == "production":
            insecure_key = "change_this_to_a_secure_random_key_in_production"
            if self.SECRET_KEY == insecure_key or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "PRODUCTION STARTUP BLOCKED: SECRET_KEY is insecure. "
                    "Generate one with: openssl rand -hex 32"
                )
            if self.POSTGRES_PASSWORD in ("postgres", "password", "", "changeme"):
                raise ValueError(
                    "PRODUCTION STARTUP BLOCKED: POSTGRES_PASSWORD is insecure."
                )
            if not self.WHATSAPP_APP_SECRET:
                raise ValueError(
                    "PRODUCTION STARTUP BLOCKED: WHATSAPP_APP_SECRET must be set "
                    "for Meta webhook signature verification."
                )
        return self

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"debug", "info", "warning", "error", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.lower()


settings = Settings()
