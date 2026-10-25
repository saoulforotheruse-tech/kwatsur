"""Adaptateur Meterless : achemine les appels Nemotron via le Meterless Runtime.

D'après le contrat public (docs/agent-ready/add-meterless-provider.md du dépôt Meterless) :
- API compatible OpenAI, par défaut sur http://127.0.0.1:8088/v1 ;
- « Authorization: Bearer <jeton> », jeton écrit par le runtime dans <stateDir>/proxy-token ;
- en-têtes « meterless-app » (identifiant stable) et « meterless-scope: user » pour le chat ;
- délai de 180 s, car le chargement d'un modèle peut prendre plusieurs minutes.
"""

import re

import httpx

from app.integrations.llm.openai_compatible import ChatCompletionClient

MINIMUM_TIMEOUT_SECONDS = 180.0
KNOWN_SUFFIXES = re.compile(r"(/v1)?(/chat/completions|/models|/healthz)?/*$")


def normalize_meterless_base_url(url: str) -> str:
    """Accepte une URL avec ou sans schéma, /v1, /v1/models… et renvoie <hôte>/v1."""
    cleaned = url.strip()
    if not cleaned:
        return ""
    if "://" not in cleaned:
        cleaned = f"http://{cleaned}"
    return KNOWN_SUFFIXES.sub("", cleaned) + "/v1"


def build_meterless_chat_client(
    base_url: str,
    runtime_token: str,
    model: str,
    app_id: str,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None = None,
) -> ChatCompletionClient:
    return ChatCompletionClient(
        base_url=normalize_meterless_base_url(base_url),
        api_key=runtime_token,
        model=model,
        timeout_seconds=max(timeout_seconds, MINIMUM_TIMEOUT_SECONDS),
        provider_label="Nemotron via Meterless",
        extra_headers={"meterless-app": app_id.lower(), "meterless-scope": "user"},
        transport=transport,
    )
