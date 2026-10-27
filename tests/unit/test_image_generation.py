"""Fournisseur Cloudflare Workers AI testé avec des réponses HTTP simulées (aucun crédit consommé)."""

import base64
import json

import httpx
import pytest

from app.core.config import Settings
from app.integrations.image_generation.base import (
    DisabledImageProvider,
    ImageGenerationNotConfiguredError,
    ImageProviderAuthenticationError,
    ImageProviderQuotaError,
    ImageProviderUnavailableError,
    InvalidGeneratedImageError,
    UnknownImageProviderError,
)
from app.integrations.image_generation.cloudflare_provider import CloudflareImageProvider
from app.integrations.image_generation.factory import build_image_provider
from tests.fakes import TINY_PNG

MODEL = "@cf/black-forest-labs/flux-1-schnell"


def make_provider(handler, account_id: str = "acc123", api_token: str = "jeton-de-test") -> CloudflareImageProvider:
    return CloudflareImageProvider(
        account_id=account_id,
        api_token=api_token,
        model=MODEL,
        steps=4,
        transport=httpx.MockTransport(handler),
    )


def success_response(image_bytes: bytes = TINY_PNG) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "result": {"image": base64.b64encode(image_bytes).decode()},
            "success": True,
            "errors": [],
            "messages": [],
        },
    )


def test_sends_documented_request_and_decodes_image() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        return success_response()

    image = make_provider(handler).generate_image("Salon lumineux")

    assert captured["url"] == f"https://api.cloudflare.com/client/v4/accounts/acc123/ai/run/{MODEL}"
    assert captured["auth"] == "Bearer jeton-de-test"
    # Le schéma du modèle n'accepte que prompt et steps (additionalProperties: false).
    assert captured["body"] == {"prompt": "Salon lumineux", "steps": 4}
    assert image.data == TINY_PNG
    assert image.content_type == "image/png"
    assert (image.provider, image.model) == ("cloudflare", MODEL)


def test_prompt_is_cut_to_the_documented_maximum() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return success_response()

    make_provider(handler).generate_image("x" * 3000)

    assert len(captured["body"]["prompt"]) == 2048


def test_missing_credentials_are_reported_without_any_call() -> None:
    calls: list[int] = []
    provider = make_provider(lambda _request: calls.append(1) or success_response(), account_id="", api_token="")

    with pytest.raises(ImageGenerationNotConfiguredError, match="CLOUDFLARE_ACCOUNT_ID"):
        provider.generate_image("Salon")
    assert calls == []
    assert provider.is_configured is False


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, ImageProviderAuthenticationError),
        (403, ImageProviderAuthenticationError),
        (404, ImageProviderAuthenticationError),
        (429, ImageProviderQuotaError),
        (500, ImageProviderUnavailableError),
        (400, InvalidGeneratedImageError),
    ],
)
def test_http_errors_become_common_errors(status: int, error_type: type) -> None:
    provider = make_provider(lambda _request: httpx.Response(status, json={"errors": [{"code": 1}]}))

    with pytest.raises(error_type):
        provider.generate_image("Salon")


def test_timeout_is_reported_as_unavailable_and_not_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ReadTimeout("trop long", request=request)

    with pytest.raises(ImageProviderUnavailableError):
        make_provider(handler).generate_image("Salon")
    assert calls == [1]


@pytest.mark.parametrize(
    "payload",
    [
        {"success": True, "result": {}},
        {"success": False, "result": {"image": "AAAA"}},
        {"success": True, "result": {"image": "pas-du-base64!"}},
        {"success": True, "result": {"image": base64.b64encode(b"<html>pas une image</html>").decode()}},
    ],
)
def test_invalid_responses_are_rejected(payload: dict) -> None:
    provider = make_provider(lambda _request: httpx.Response(200, json=payload))

    with pytest.raises(InvalidGeneratedImageError):
        provider.generate_image("Salon")


def test_factory_builds_cloudflare_by_default() -> None:
    settings = Settings(_env_file=None, cloudflare_account_id="acc", cloudflare_api_token="tok")

    provider = build_image_provider(settings)

    assert isinstance(provider, CloudflareImageProvider)
    assert provider.is_configured


def test_factory_respects_disabled_generation() -> None:
    settings = Settings(_env_file=None, image_generation_enabled=False)

    assert isinstance(build_image_provider(settings), DisabledImageProvider)


def test_unknown_provider_is_an_explicit_error() -> None:
    settings = Settings(_env_file=None, image_generation_provider="inconnu")

    with pytest.raises(UnknownImageProviderError, match="inconnu"):
        build_image_provider(settings)


def test_vision_describer_sends_image_bytes_as_documented() -> None:
    from app.integrations.image_description.cloudflare_describer import CloudflareImageDescriber

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"success": True, "result": {"description": " Murs blancs. "}})

    describer = CloudflareImageDescriber("acc123", "jeton", "@cf/llava-hf/llava-1.5-7b-hf", transport=httpx.MockTransport(handler))

    assert describer.describe(TINY_PNG, "Décris") == "Murs blancs."
    assert captured["url"].endswith("/accounts/acc123/ai/run/@cf/llava-hf/llava-1.5-7b-hf")
    assert captured["body"]["image"] == list(TINY_PNG)
    assert captured["body"]["prompt"] == "Décris"
