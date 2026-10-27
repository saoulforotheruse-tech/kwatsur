"""Fournisseur Cloudflare Workers AI (modèle par défaut : FLUX.1 schnell).

Contrat vérifié dans la documentation officielle (octobre 2026) :
- POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}
  avec « Authorization: Bearer <jeton> » ;
- corps : {"prompt": texte de 1 à 2048 caractères, "steps": entier ≤ 8, 4 par défaut} ;
  aucun autre champ n'est accepté par le schéma du modèle ;
- réponse : enveloppe Cloudflare {"success", "errors", "result": {"image": base64}}.
La documentation ne garantit pas le format (JPEG ou PNG) ni les codes d'erreur :
le format est déduit des octets, et les statuts HTTP sont traités prudemment.
Aucune relance automatique : chaque appel consomme du quota.
"""

import base64
import binascii
import logging

import httpx

from app.core.image_formats import detect_image_type
from app.integrations.image_generation.base import (
    GeneratedImage,
    ImageGenerationNotConfiguredError,
    ImageProviderAuthenticationError,
    ImageProviderQuotaError,
    ImageProviderUnavailableError,
    InvalidGeneratedImageError,
)

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.cloudflare.com/client/v4"
MAX_PROMPT_LENGTH = 2048


class CloudflareImageProvider:
    name = "cloudflare"

    def __init__(
        self,
        account_id: str,
        api_token: str,
        model: str,
        steps: int = 4,
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.account_id = account_id.strip()
        self.api_token = api_token.strip()
        self.model = model.strip()
        self.steps = steps
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @property
    def is_configured(self) -> bool:
        return bool(self.account_id and self.api_token and self.model)

    def generate_image(self, prompt: str) -> GeneratedImage:
        """Envoie la description à Cloudflare et renvoie l'image décodée et vérifiée."""
        if not self.is_configured:
            raise ImageGenerationNotConfiguredError(
                "La génération d'images n'est pas configurée : renseignez CLOUDFLARE_ACCOUNT_ID "
                "et CLOUDFLARE_API_TOKEN dans le fichier .env."
            )
        response = self._post_prompt(prompt[:MAX_PROMPT_LENGTH])
        self._raise_for_status(response)
        image_bytes = self._decode_image(response)
        content_type = detect_image_type(image_bytes)
        if content_type is None:
            raise InvalidGeneratedImageError("Cloudflare a renvoyé un contenu qui n'est pas une image.")
        return GeneratedImage(
            data=image_bytes, content_type=content_type, provider=self.name, model=self.model
        )

    def _run_url(self) -> str:
        return f"{API_BASE_URL}/accounts/{self.account_id}/ai/run/{self.model}"

    def _post_prompt(self, prompt: str) -> httpx.Response:
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as http:
                return http.post(
                    self._run_url(),
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json={"prompt": prompt, "steps": self.steps},
                )
        except httpx.TimeoutException as error:
            raise ImageProviderUnavailableError(
                "Cloudflare n'a pas répondu à temps. Réessayez dans un instant."
            ) from error
        except httpx.HTTPError as error:
            raise ImageProviderUnavailableError("Cloudflare est injoignable.") from error

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        if status < 400:
            return
        # Seuls le statut et le code d'erreur Cloudflare sont journalisés : jamais le jeton.
        logger.warning(
            "Cloudflare Workers AI a répondu %s (modèle %s, erreurs %s)",
            status, self.model, _error_codes(response),
        )
        if status in (401, 403):
            raise ImageProviderAuthenticationError()
        if status == 404:
            raise ImageProviderAuthenticationError(
                "Cloudflare ne trouve pas ce compte ou ce modèle : vérifiez CLOUDFLARE_ACCOUNT_ID "
                "et CLOUDFLARE_IMAGE_MODEL."
            )
        if status == 429:
            raise ImageProviderQuotaError()
        if status >= 500:
            raise ImageProviderUnavailableError()
        raise InvalidGeneratedImageError("Cloudflare a refusé la requête de génération.")

    def _decode_image(self, response: httpx.Response) -> bytes:
        try:
            envelope = response.json()
            encoded_image = envelope["result"]["image"]
        except (ValueError, KeyError, TypeError) as error:
            raise InvalidGeneratedImageError("Réponse Cloudflare sans image.") from error
        if envelope.get("success") is False or not isinstance(encoded_image, str) or not encoded_image:
            raise InvalidGeneratedImageError("Cloudflare n'a pas produit d'image.")
        try:
            return base64.b64decode(encoded_image, validate=True)
        except (binascii.Error, ValueError) as error:
            raise InvalidGeneratedImageError("Image Cloudflare mal encodée.") from error


def _error_codes(response: httpx.Response) -> list:
    try:
        return [error.get("code") for error in response.json().get("errors", [])]
    except (ValueError, AttributeError, TypeError):
        return []
