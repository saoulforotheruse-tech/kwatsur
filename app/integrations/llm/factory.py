"""Sélection du fournisseur IA selon la configuration (LLM_PROVIDER)."""

from app.core.config import Settings
from app.integrations.agent_runtime.meterless import build_meterless_chat_client
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.nemotron import DisabledLLMProvider, NemotronProvider
from app.integrations.llm.openai_compatible import ChatCompletionClient
from app.integrations.llm.rules import RuleBasedProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "meterless":
        client = build_meterless_chat_client(
            base_url=settings.meterless_base_url,
            runtime_token=settings.meterless_api_key,
            model=settings.meterless_model,
            app_id=settings.meterless_app_id,
            timeout_seconds=settings.llm_timeout_seconds,
            thinking_enabled=settings.llm_thinking_enabled,
        )
        return NemotronProvider(client, name="meterless")
    if settings.llm_provider == "nemotron":
        client = ChatCompletionClient(
            base_url=settings.nemotron_base_url,
            api_key=settings.nemotron_api_key,
            model=settings.nemotron_model,
            timeout_seconds=settings.llm_timeout_seconds,
            provider_label="Nemotron",
            thinking_enabled=settings.llm_thinking_enabled,
        )
        return NemotronProvider(client, name="nemotron")
    if settings.llm_provider == "rules":
        return RuleBasedProvider()
    return DisabledLLMProvider()
