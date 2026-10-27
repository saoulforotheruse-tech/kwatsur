"""Seul endroit où le fournisseur de description de photos est choisi (même fournisseur que la génération)."""

from app.core.config import Settings
from app.integrations.image_description.base import DisabledImageDescriber, ImageDescriber
from app.integrations.image_description.cloudflare_describer import CloudflareImageDescriber
from app.integrations.image_generation.base import UnknownImageProviderError


def build_image_describer(settings: Settings) -> ImageDescriber:
    if not (settings.image_generation_enabled and settings.image_description_enabled):
        return DisabledImageDescriber()
    provider_name = settings.image_generation_provider.strip().lower()
    if provider_name == "cloudflare":
        return CloudflareImageDescriber(
            account_id=settings.cloudflare_account_id,
            api_token=settings.cloudflare_api_token,
            model=settings.cloudflare_vision_model,
            timeout_seconds=settings.image_generation_timeout_seconds,
        )
    raise UnknownImageProviderError(
        f"Fournisseur d'images inconnu : « {provider_name} ». Valeur possible : cloudflare."
    )
