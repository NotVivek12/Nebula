"""
LLM provider dispatcher.

Resolves which LLM provider to use for a given business.
Provider resolution order:
  1. Per-business Integration record (tenant-specific key)
  2. Global NVIDIA API key from settings (if no integration configured)
  3. Raise ValueError (not configured)

Supported providers: nvidia, openai, gemini, anthropic, openrouter
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.integration import Integration
from app.services.llm.anthropic import AnthropicLLMProvider
from app.services.llm.base import BaseLLMProvider
from app.services.llm.gemini import GeminiLLMProvider
from app.services.llm.nvidia import NvidiaNIMProvider
from app.services.llm.openai import OpenAILLMProvider
from app.services.llm.openrouter import OpenRouterLLMProvider

_PROVIDER_MAP: dict[str, type] = {
    "openai": OpenAILLMProvider,
    "gemini": GeminiLLMProvider,
    "anthropic": AnthropicLLMProvider,
    "openrouter": OpenRouterLLMProvider,
    "nvidia": NvidiaNIMProvider,
}


def _instantiate_provider(provider_name: str, api_key: str, extra_creds: dict | None = None) -> BaseLLMProvider:
    """Instantiates a provider class by name."""
    cls = _PROVIDER_MAP.get(provider_name.lower())
    if cls is None:
        raise ValueError(f"Unsupported LLM provider: '{provider_name}'")
    if provider_name.lower() == "nvidia":
        base_url = (extra_creds or {}).get("base_url") or settings.NVIDIA_BASE_URL
        return cls(api_key=api_key, base_url=base_url)  # type: ignore[call-arg]
    return cls(api_key=api_key)  # type: ignore[call-arg]


async def get_llm_provider(
    business_id: uuid.UUID,
    provider_name: str,
    db: AsyncSession,
) -> BaseLLMProvider:
    """
    Resolves and returns the correct LLM provider for a business.

    Steps:
    1. Looks for a matching active Integration record for the business.
    2. If found, uses credentials from that record.
    3. If not found, falls back to global API keys from settings (NVIDIA by default).
    4. Raises ValueError if neither is configured.
    """
    clean_name = provider_name.lower().strip()

    # 1. Look for per-business integration
    query = (
        select(Integration)
        .where(Integration.business_id == business_id)
        .where(Integration.provider == clean_name)
        .where(Integration.is_active.is_(True))
    )
    result = await db.execute(query)
    integration = result.scalar_one_or_none()

    if integration:
        creds = integration.credentials
        api_key = creds.get("api_key")
        if not api_key:
            raise ValueError(
                f"API key missing from {provider_name} integration credentials "
                f"for business {business_id}"
            )
        return _instantiate_provider(clean_name, str(api_key), creds)

    # 2. Fall back to global settings keys
    global_key = _get_global_api_key(clean_name)
    if global_key:
        return _instantiate_provider(clean_name, global_key)

    raise ValueError(
        f"No active {provider_name} credentials configured. "
        f"Set NVIDIA_API_KEY (or equivalent) in environment, or configure an integration."
    )


def _get_global_api_key(provider_name: str) -> str:
    """Returns global API key for a provider from settings, or empty string."""
    keys = {
        "openai": settings.OPENAI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
        "openrouter": settings.OPENROUTER_API_KEY,
        "nvidia": settings.NVIDIA_API_KEY,
    }
    return keys.get(provider_name, "")


async def get_default_llm_provider(
    business_id: uuid.UUID,
    db: AsyncSession,
) -> BaseLLMProvider:
    """
    Returns the default LLM provider for a business.

    Tries providers in order of preference:
    1. NVIDIA Nemotron (default)
    2. OpenAI
    3. Anthropic
    4. Gemini
    """
    for provider in [settings.DEFAULT_AI_PROVIDER, "openai", "anthropic", "gemini"]:
        try:
            return await get_llm_provider(business_id, provider, db)
        except ValueError:
            continue

    raise ValueError(
        "No AI provider configured. Set NVIDIA_API_KEY, OPENAI_API_KEY, "
        "ANTHROPIC_API_KEY, or GEMINI_API_KEY in your environment."
    )
