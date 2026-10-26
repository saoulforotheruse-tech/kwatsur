"""Clients IA (Nemotron direct et via Meterless) testés avec des réponses HTTP simulées."""

import json

import httpx
import pytest

from app.core.exceptions import (
    IntegrationNotConfiguredError,
    IntegrationUnavailableError,
    InvalidIntegrationResponseError,
)
from app.integrations.agent_runtime.meterless import (
    build_meterless_chat_client,
    normalize_meterless_base_url,
)
from app.integrations.llm.nemotron import NemotronProvider, parse_json_object
from app.integrations.llm.openai_compatible import ChatCompletionClient
from app.schemas.criteria import SearchCriteria


def completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def make_client(handler, api_key: str = "test-key") -> ChatCompletionClient:
    return ChatCompletionClient(
        base_url="https://llm.test/v1",
        api_key=api_key,
        model="nvidia/test-model",
        timeout_seconds=5,
        provider_label="Nemotron",
        transport=httpx.MockTransport(handler),
    )


def test_sends_openai_compatible_request_and_strips_reasoning() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        return completion("<think>raisonnement interne</think>\nBonjour !")

    answer = make_client(handler).complete([{"role": "user", "content": "Salut"}])

    assert answer == "Bonjour !"
    assert captured["url"] == "https://llm.test/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"
    assert captured["body"]["model"] == "nvidia/test-model"


def test_strips_reasoning_when_opening_tag_is_missing() -> None:
    # Forme observée via Meterless avec Nemotron 3 Ultra : pas de <think> ouvrant.
    client = make_client(lambda _request: completion("L'utilisateur veut une phrase.</think>Bonjour !"))

    assert client.complete([{"role": "user", "content": "Salut"}]) == "Bonjour !"


@pytest.mark.parametrize(
    ("status", "message_part"),
    [(401, "clé"), (429, "Quota"), (500, "refusé")],
)
def test_http_errors_become_readable_errors(status: int, message_part: str) -> None:
    client = make_client(lambda _request: httpx.Response(status, json={"error": "x"}))

    with pytest.raises(IntegrationUnavailableError) as error:
        client.complete([{"role": "user", "content": "x"}])

    assert message_part in error.value.public_message


def test_transient_provider_error_is_retried_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.integrations.llm.openai_compatible.time.sleep", lambda _seconds: None)
    responses = [httpx.Response(502, json={"error": "fetch failed"}), completion("Bonjour !")]

    answer = make_client(lambda _request: responses.pop(0)).complete([{"role": "user", "content": "Salut"}])

    assert answer == "Bonjour !"


def test_persistent_provider_error_is_reported_after_one_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.integrations.llm.openai_compatible.time.sleep", lambda _seconds: None)
    calls: list[int] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(502, json={"error": "fetch failed"})

    with pytest.raises(IntegrationUnavailableError):
        make_client(handler).complete([{"role": "user", "content": "Salut"}])
    assert len(calls) == 2


def test_timeout_is_reported_as_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("trop long", request=request)

    with pytest.raises(IntegrationUnavailableError, match="à temps"):
        make_client(handler).complete([{"role": "user", "content": "x"}])


def test_malformed_payload_is_invalid_response() -> None:
    client = make_client(lambda _request: httpx.Response(200, json={"unexpected": True}))

    with pytest.raises(InvalidIntegrationResponseError):
        client.complete([{"role": "user", "content": "x"}])


def test_missing_key_means_not_configured_without_network_call() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Aucun appel réseau ne doit partir sans clé.")

    with pytest.raises(IntegrationNotConfiguredError):
        make_client(handler, api_key="").complete([{"role": "user", "content": "x"}])


def test_parse_json_object_handles_code_fences() -> None:
    assert parse_json_object('Voici :\n```json\n{"intent": "search"}\n```') == {"intent": "search"}


def test_extraction_is_validated_and_retried_once() -> None:
    answers = iter(["pas du JSON", json.dumps({"intent": "search", "updates": {"city": "douala", "max_rent": 150000}})])
    provider = NemotronProvider(make_client(lambda _request: completion(next(answers))))

    extraction = provider.extract_criteria("Un appart à Douala", [], SearchCriteria())

    assert extraction.updates.city == "douala"
    assert extraction.updates.max_rent == 150000


def test_extraction_fails_cleanly_after_second_invalid_answer() -> None:
    provider = NemotronProvider(make_client(lambda _request: completion("toujours pas de JSON")))

    with pytest.raises(InvalidIntegrationResponseError):
        provider.extract_criteria("Bonjour", [], SearchCriteria())


@pytest.mark.parametrize(
    "pasted_url",
    ["127.0.0.1:8088", "http://127.0.0.1:8088/v1", "http://127.0.0.1:8088/v1/models", "http://127.0.0.1:8088/healthz"],
)
def test_meterless_url_is_normalized_once(pasted_url: str) -> None:
    assert normalize_meterless_base_url(pasted_url) == "http://127.0.0.1:8088/v1"


def test_meterless_client_sends_required_headers() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(request.headers)
        return completion("OK")

    client = build_meterless_chat_client(
        "127.0.0.1:8088", "runtime-token", "meterless/auto", "Kwatsur", 30,
        transport=httpx.MockTransport(handler),
    )
    client.complete([{"role": "user", "content": "x"}])

    assert captured["meterless-app"] == "kwatsur"
    assert captured["meterless-scope"] == "user"
    assert captured["authorization"] == "Bearer runtime-token"
    assert client.timeout_seconds == 180
