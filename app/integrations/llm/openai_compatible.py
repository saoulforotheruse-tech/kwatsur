"""Client HTTP pour les API « chat completions » compatibles OpenAI.

Utilisé pour Nemotron sur le catalogue NVIDIA (https://integrate.api.nvidia.com/v1)
et pour le Meterless Runtime local, qui expose le même protocole.
"""

import logging
import re
from typing import Any

import httpx

from app.core.exceptions import (
    IntegrationNotConfiguredError,
    IntegrationUnavailableError,
    InvalidIntegrationResponseError,
)

logger = logging.getLogger(__name__)

# Les modèles de raisonnement Nemotron peuvent préfixer leur réponse d'un bloc <think>.
THINK_BLOCK_PATTERN = re.compile(r"<think>.*?(</think>|$)", re.DOTALL | re.IGNORECASE)
# Via Meterless, la balise ouvrante peut manquer : tout ce qui précède </think> est du raisonnement.
ORPHAN_THINK_END_PATTERN = re.compile(r"^.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    text = THINK_BLOCK_PATTERN.sub("", text)
    return ORPHAN_THINK_END_PATTERN.sub("", text).strip()


class ChatCompletionClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        provider_label: str,
        extra_headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.provider_label = provider_label
        self.extra_headers = extra_headers or {}
        self.transport = transport

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        if not self.is_configured:
            raise IntegrationNotConfiguredError(
                f"Le modèle IA ({self.provider_label}) n'est pas configuré."
            )
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": 0.95,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", **self.extra_headers}
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as http:
                response = http.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
        except httpx.TimeoutException as error:
            raise IntegrationUnavailableError(
                f"Le modèle IA ({self.provider_label}) n'a pas répondu à temps."
            ) from error
        except httpx.HTTPError as error:
            raise IntegrationUnavailableError(
                f"Le modèle IA ({self.provider_label}) est injoignable."
            ) from error

        if response.status_code in (401, 403):
            raise IntegrationUnavailableError(
                f"Le modèle IA ({self.provider_label}) a refusé la clé d'accès."
            )
        if response.status_code == 429:
            raise IntegrationUnavailableError(
                f"Quota du modèle IA ({self.provider_label}) atteint. Réessayez plus tard."
            )
        if response.status_code >= 400:
            logger.warning("%s a répondu %s", self.provider_label, response.status_code)
            raise IntegrationUnavailableError(
                f"Le modèle IA ({self.provider_label}) a refusé la requête."
            )

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise InvalidIntegrationResponseError(
                f"Réponse inattendue du modèle IA ({self.provider_label})."
            ) from error
        if not isinstance(content, str) or not strip_reasoning(content):
            raise InvalidIntegrationResponseError(
                f"Le modèle IA ({self.provider_label}) a renvoyé une réponse vide."
            )
        return strip_reasoning(content)
