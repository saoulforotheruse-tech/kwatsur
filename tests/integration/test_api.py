"""Endpoints principaux via le client HTTP de FastAPI."""

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import get_llm_provider
from app.core.rate_limit import SlidingWindowRateLimiter
from app.db.session import get_session
from app.integrations.llm.nemotron import DisabledLLMProvider
from app.main import app
from tests.fakes import MockLLMProvider, scripted_extractions


def test_health_reports_database_and_configuration(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.json()["listing_source"] == "postgres"


def test_property_search_filters_and_explains(client: TestClient) -> None:
    response = client.get(
        "/api/properties", params={"city": "Douala", "max_rent": 150000, "bedrooms": 2}
    )

    body = response.json()
    assert response.status_code == 200
    assert body["data_source"] == "postgres"
    assert body["total"] > 0
    for result in body["results"]:
        assert result["property"]["city"] == "Douala"
        assert result["property"]["monthly_rent"] <= 150000
        assert result["property"]["source_is_demo"] is True
        assert result["reasons"]


def test_invalid_rent_range_returns_validation_error(client: TestClient) -> None:
    response = client.get("/api/properties", params={"min_rent": 200000, "max_rent": 100000})

    assert response.status_code == 422


def test_property_detail_and_contact_draft(client: TestClient) -> None:
    assert client.get("/api/properties/999").status_code == 404

    detail = client.get("/api/properties/1")
    draft = client.post("/api/properties/1/contact-draft")

    assert detail.status_code == 200
    assert draft.status_code == 200
    assert detail.json()["title"] in draft.json()["message"]
    assert "n'envoie aucun message" in draft.json()["notice"]


def test_chat_round_trip_and_conversation_reading(
    client: TestClient, mock_llm: MockLLMProvider
) -> None:
    mock_llm.extraction_rule = scripted_extractions(
        {"intent": "search", "updates": {"city": "Douala", "max_rent": 150000}}
    )

    chat = client.post("/api/chat", json={"message": "Un logement à Douala, 150 000 max"})
    conversation_id = chat.json()["conversation_id"]
    history = client.get(f"/api/conversations/{conversation_id}")

    assert chat.status_code == 200
    assert chat.json()["searched"] is True
    assert history.json()["criteria"]["max_rent"] == 150000
    assert [message["role"] for message in history.json()["messages"]] == ["user", "assistant"]


def test_unknown_conversation_returns_404(client: TestClient) -> None:
    assert client.get("/api/conversations/inconnue").status_code == 404
    response = client.post("/api/chat", json={"message": "Bonjour", "conversation_id": "inconnue"})
    assert response.status_code == 404


def test_chat_without_configured_model_returns_clear_503(client: TestClient) -> None:
    app.dependency_overrides[get_llm_provider] = DisabledLLMProvider

    response = client.post("/api/chat", json={"message": "Un studio à Yaoundé"})

    assert response.status_code == 503
    assert "désactivé" in response.json()["detail"]


def test_empty_message_is_rejected(client: TestClient) -> None:
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_chat_rate_limit(client: TestClient, mock_llm: MockLLMProvider) -> None:
    app.state.chat_rate_limiter = SlidingWindowRateLimiter(max_calls=1)
    mock_llm.extraction_rule = scripted_extractions({"intent": "other"}, {"intent": "other"})

    assert client.post("/api/chat", json={"message": "a"}).status_code == 200
    assert client.post("/api/chat", json={"message": "b"}).status_code == 429


def test_integrations_status_without_credentials(client: TestClient) -> None:
    response = client.get("/api/integrations/status")

    statuses = {item["name"]: item["status"] for item in response.json()}
    assert statuses["zetaris"] == "not_configured"
    assert statuses["llm"] == "disabled"


def test_database_failure_returns_generic_service_error(session: Session) -> None:
    def unavailable_session() -> Generator[Session, None, None]:
        raise OperationalError("SELECT 1", {}, RuntimeError("connection details"))
        yield

    app.dependency_overrides[get_session] = unavailable_session
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "connection details" not in response.text


def test_demo_mode_answers_without_any_model_or_key(client: TestClient) -> None:
    from app.api.dependencies import get_scout_engine
    from app.engines.scout import ModelProfile, ScoutEngine
    from app.integrations.llm.rules import RuleBasedProvider

    app.dependency_overrides[get_llm_provider] = RuleBasedProvider
    app.dependency_overrides[get_scout_engine] = lambda: ScoutEngine(
        ModelProfile("rules", "règles déterministes (mode démo)", False), "secret-de-test"
    )

    body = client.post("/api/chat", json={"message": "Un appartement à Douala, 150 000 FCFA max"}).json()

    assert body["searched"] is True and body["total"] > 0
    assert body["reply_generated_by"] == "template"
    assert body["scout"]["tool_plan"] == ["search_service.search", "template.explain"]
    assert any("Mode démo" in notice for notice in body["notices"])
    assert all(item["property"]["monthly_rent"] <= 150000 for item in body["results"])


def test_chat_abroad_searches_by_country_and_says_untera_is_missing(
    client: TestClient, mock_llm: MockLLMProvider
) -> None:
    # Pays hors Cameroun sans ville : pas de question sur la ville, recherche routée vers Untera
    # (non configuré dans les tests : aucun appel réseau, la réponse le dit).
    mock_llm.extraction_rule = scripted_extractions(
        {"intent": "search", "updates": {"country": "US", "transaction": "rent"}}
    )

    chat = client.post("/api/chat", json={"message": "i want to book a house low rent in the USA"})

    assert chat.status_code == 200
    body = chat.json()
    assert body["searched"] is True
    assert body["data_source"] == "untera"
    assert body["criteria"]["country"] == "US"
    assert any("UNTERA_API_KEY" in notice for notice in body["notices"])
    assert body["results"] == []


def test_chat_shows_untera_photos_on_request(
    client: TestClient, mock_llm: MockLLMProvider, session: Session
) -> None:
    from app.api.dependencies import get_search_service
    from app.integrations.data.postgres import PostgresListingSource
    from app.repositories.property_repository import PropertyRepository
    from app.services.ranking_service import RankingService
    from app.services.risk_service import RiskService
    from app.services.search_service import SearchService
    from tests.unit.test_untera import ORIGIN, REAL_RESPONSE, FakeUnteraSource
    from app.integrations.data.untera import item_to_property

    house = item_to_property(REAL_RESPONSE["results"][0], ORIGIN)
    app.dependency_overrides[get_search_service] = lambda: SearchService(
        PostgresListingSource(PropertyRepository(session)), RankingService(), RiskService(),
        international_source=FakeUnteraSource([], [house]),
    )
    mock_llm.extraction_rule = scripted_extractions(
        {"intent": "search", "updates": {"country": "PT", "property_type": "maison"}}
    )

    search = client.post("/api/chat", json={"message": "Je cherche une maison à Belmonte au Portugal"})
    conversation_id = search.json()["conversation_id"]
    photos = client.post(
        "/api/chat", json={"message": "Montre-moi des photos du n°1", "conversation_id": conversation_id}
    )

    assert search.json()["data_source"] == "untera"
    assert search.json()["results"][0]["images"][0]["kind"] == "source_photo"
    body = photos.json()
    assert body["scout"]["intent"] == "listing.visualize"
    assert [image["url"] for image in body["images"]] == house.photo_urls[:4]
    assert all(image["is_ai_generated"] is False for image in body["images"])
    assert "annonce d'origine" in body["reply"]
