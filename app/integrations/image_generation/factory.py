"""Seul endroit où le fournisseur de génération d'images est choisi (IMAGE_GENERATION_PROVIDER)."""

from app.core.config import Settings
from app.integrations.image_generation.base import (
    DisabledImageProvider,
    ImageGenerationProvider,
    UnknownImageProviderError,
)
from app.integrations.image_generation.cloudflare_provider import CloudflareImageProvider


def build_image_provider(settings: Settings) -> ImageGenerationProvider:
    if not settings.image_generation_enabled:
        return DisabledImageProvider()
    provider_name = settings.image_generation_provider.strip().lower()
    if provider_name == "cloudflare":
        return CloudflareImageProvider(
            account_id=settings.cloudflare_account_id,
            api_token=settings.cloudflare_api_token,
            model=settings.cloudflare_image_model,
            steps=settings.cloudflare_image_steps,
            timeout_seconds=settings.image_generation_timeout_seconds,
        )
    # Jamais de remplacement silencieux par un autre fournisseur.
    raise UnknownImageProviderError(
        f"Fournisseur d'images inconnu : « {provider_name} ». Valeur possible : cloudflare."
    )
