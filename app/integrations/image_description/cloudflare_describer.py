"""Description de photos par Cloudflare Workers AI (modèle par défaut : LLaVA 1.5 7B, bêta).

Contrat vérifié dans la documentation officielle (octobre 2026), schéma du modèle
@cf/llava-hf/llava-1.5-7b-hf :
- entrée : {"image": tableau d'entiers 0-255 (octets de l'image), "prompt": texte,
  "max_tokens": entier (512 par défaut)} ; « image » est le seul champ obligatoire ;
- sortie : {"description": texte}, dans l'enveloppe Cloudflare {"success", "result"}.
Pas d'étape d'acceptation de licence pour ce modèle. Aucune relance automatique.
"""

import logging

import httpx

from app.integrations.image_generation.base import (
    ImageGenerationNotConfiguredError,
    ImageProviderAuthenticationError,
    ImageProviderQuotaError,
    ImageProviderUnavailableError,
    InvalidGeneratedImageError,
)
from app.integrations.image_generation.cloudflare_provider import API_BASE_URL

logger = logging.getLogger(__name__)

MAX_DESCRIPTION_TOKENS = 160


class CloudflareImageDescriber:
    name = "cloudflare"

    def __init__(
        self,
        account_id: str,
        api_token: str,
        model: str,
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.account_id = account_id.strip()
        self.api_token = api_token.strip()
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @property
    def is_configured(self) -> bool:
        return bool(self.account_id and self.api_token and self.model)

    def describe(self, image_bytes: bytes, question: str) -> str:
        if not self.is_configured:
            raise ImageGenerationNotConfiguredError("La description des photos n'est pas configurée.")
        payload = {
            # Le schéma attend les octets de l'image sous forme de liste d'entiers 0-255.
            "image": list(image_bytes),
            "prompt": question,
            "max_tokens": MAX_DESCRIPTION_TOKENS,
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as http:
                response = http.post(
                    f"{API_BASE_URL}/accounts/{self.account_id}/ai/run/{self.model}",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json=payload,
                )
        except httpx.HTTPError as error:
            raise ImageProviderUnavailableError("Cloudflare est injoignable pour décrire la photo.") from error
        return self._description_from(response)

    def _description_from(self, response: httpx.Response) -> str:
        if response.status_code in (401, 403, 404):
            raise ImageProviderAuthenticationError()
        if response.status_code == 429:
            raise ImageProviderQuotaError()
        if response.status_code >= 500:
            raise ImageProviderUnavailableError()
        if response.status_code >= 400:
            logger.warning("Description de photo refusée par Cloudflare (%s, modèle %s)", response.status_code, self.model)
            raise InvalidGeneratedImageError("Cloudflare a refusé la description de la photo.")
        try:
            description = response.json()["result"]["description"]
        except (ValueError, KeyError, TypeError) as error:
            raise InvalidGeneratedImageError("Réponse Cloudflare sans description.") from error
        if not isinstance(description, str) or not description.strip():
            raise InvalidGeneratedImageError("Cloudflare n'a pas décrit la photo.")
        return description.strip()
