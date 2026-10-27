"""Proposition d'annonce dans le chat, photos, validation admin et images d'une pièce (de bout en bout)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_settings
from app.core.exceptions import IntegrationUnavailableError
from app.integrations.llm.rules import parse_listing
from app.main import app
from app.models.image import PropertyImage
from app.services.image_storage import LocalImageStore
from tests.conftest import make_test_settings
from tests.fakes import TINY_PNG, FakeImageProvider, MockLLMProvider, scripted_extractions

ADMIN = {"X-Admin-Token": "admin-de-test"}


@pytest.mark.parametrize("scout_routing", [True, False])
@pytest.mark.parametrize("kind", [
    "owner_photo", "sample_photo", "ai_generated_illustration", "ai_edited_photo",
])
def test_search_sends_image_facts_to_model_and_shows_images_in_chat(
    client: TestClient, mock_llm: MockLLMProvider, session: Session, tmp_path: Path,
    kind: str, scout_routing: bool,
) -> None:
    app.dependency_overrides[get_settings] = lambda: make_test_settings(
        scout_routing_enabled=scout_routing
    )
    store = LocalImageStore(tmp_path, max_bytes=1_000)
    file_name, content_type = store.save(TINY_PNG)
    image = PropertyImage(
        property_id=9, kind=kind, room="facade", file_name=file_name,
        content_type=content_type, size_bytes=len(TINY_PNG),
        author="Auteur de test", license="CC BY-SA 4.0",
        source_url="https://commons.wikimedia.org/wiki/File:Test.png",
        created_at=datetime.now(timezone.utc),
    )
    session.add(image)
    session.commit()
    mock_llm.extraction_rule = scripted_extractions(
        {"intent": "search", "updates": {"city": "Douala", "max_rent": 35000}},
        {"intent": "refine", "updates": {}},
    )

    first = chat(client, "Un logement à Douala, 35 000 FCFA maximum")
    follow_up = (
        "Finalement, toujours 35 000 FCFA maximum à Douala"
        if scout_routing else "Montre-moi des images du logement"
    )
    second = chat(client, follow_up, first["conversation_id"])

    for response, context in zip([first, second], mock_llm.received_contexts, strict=True):
        assert response["total"] == 1
        image_facts = context.top_results[0]["images"]
        assert len(image_facts) == 1
        stored = response["results"][0]["images"][0]
        assert image_facts[0] == {key: stored[key] for key in image_facts[0]}
        assert image_facts[0]["id"] == image.id
        assert image_facts[0]["kind"] == kind
        assert image_facts[0]["url"] == f"/api/images/{image.id}"
        shown = response["images"][0]
        assert shown["id"] == image.id and shown["kind"] == kind
        assert "Logement n°1" in shown["label"]
        assert "Chambre moderne à Bonabéri" in shown["label"]
        assert shown["caption"] == image_facts[0]["caption"]
        assert shown["credit"] == image_facts[0]["credit"]
        if kind == "sample_photo":
            assert "ne montre pas ce logement" in image_facts[0]["label"]
            assert "CC BY-SA 4.0" in shown["credit"]
        assert client.get(shown["url"]).content == TINY_PNG


def test_search_without_images_reports_an_empty_image_list(
    client: TestClient, mock_llm: MockLLMProvider,
) -> None:
    mock_llm.extraction_rule = scripted_extractions(
        {"intent": "search", "updates": {"city": "Douala"}}
    )
    response = chat(client, "Un logement à Douala")
    assert response["images"] == []
    assert all(result["images"] == [] for result in response["results"])
    assert all(result["images"] == [] for result in mock_llm.received_contexts[0].top_results)


def test_search_keeps_images_when_model_reply_fails(
    client: TestClient, mock_llm: MockLLMProvider, session: Session, tmp_path: Path,
) -> None:
    store = LocalImageStore(tmp_path, max_bytes=1_000)
    file_name, content_type = store.save(TINY_PNG)
    session.add(PropertyImage(
        property_id=9, kind="sample_photo", room="facade", file_name=file_name,
        content_type=content_type, size_bytes=len(TINY_PNG), created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    mock_llm.extraction_rule = scripted_extractions(
        {"intent": "search", "updates": {"city": "Douala", "max_rent": 35000}}
    )
    mock_llm.reply_error = IntegrationUnavailableError("Modèle indisponible.")

    response = chat(client, "Un logement à Douala, 35 000 FCFA maximum")

    assert response["reply_generated_by"] == "template"
    assert response["images"][0]["kind"] == "sample_photo"
    assert "ne montre pas ce logement" in response["images"][0]["label"]


def chat(client: TestClient, message: str, conversation_id: str | None = None) -> dict:
    response = client.post("/api/chat", json={"message": message, "conversation_id": conversation_id})
    assert response.status_code == 200, response.text
    return response.json()


def describe_listing(client: TestClient, mock_llm: MockLLMProvider) -> dict:
    """Un propriétaire décrit son logement en trois messages (règles du mode démo comme extracteur)."""
    mock_llm.listing_rule = parse_listing
    first = chat(client, "Bonjour, je loue mon appartement de 2 chambres à Douala vers Bonapriso, 130 000 FCFA")
    conversation_id = first["conversation_id"]
    assert first["scout"]["intent"] == "listing.submit"
    assert first["submission"]["status"] == "draft"
    assert first["submission"]["missing_fields"] == ["contact_information"]
    assert "joindre" in first["reply"]

    second = chat(client, "Mon numéro : 677 12 34 56", conversation_id)
    assert second["submission"]["missing_fields"] == []
    assert "oui" in second["reply"]
    return second


def test_owner_describes_listing_then_admin_approves_it(client: TestClient, mock_llm: MockLLMProvider) -> None:
    summary = describe_listing(client, mock_llm)
    conversation_id = summary["conversation_id"]
    submission_id = summary["submission"]["id"]

    # Une vraie photo, ajoutée avant l'envoi.
    photo = client.post(
        f"/api/submissions/{submission_id}/photos?room=salon",
        content=TINY_PNG,
        headers={"X-Conversation-Id": conversation_id, "Content-Type": "image/png"},
    )
    assert photo.status_code == 200, photo.text
    assert photo.json()["kind"] == "owner_photo"

    sent = chat(client, "oui", conversation_id)
    assert sent["submission"]["status"] == "pending"
    assert "administrateur" in sent["reply"]

    # Avant validation, la proposition n'apparaît pas dans les recherches.
    before = client.get("/api/properties", params={"city": "Douala", "neighborhood": "Bonapriso"}).json()
    assert all(item["property"]["source_name"] != "Annonces proposées par les propriétaires" for item in before["results"])

    pending = client.get("/api/admin/submissions", headers=ADMIN).json()
    assert [item["id"] for item in pending] == [submission_id]
    approved = client.post(f"/api/admin/submissions/{submission_id}/approve", json={"note": "OK"}, headers=ADMIN)
    assert approved.json()["status"] == "approved"

    after = client.get("/api/properties", params={"city": "Douala", "max_rent": 130000, "bedrooms": 2}).json()
    published = [item for item in after["results"] if item["property"]["source_name"] == "Annonces proposées par les propriétaires"]
    assert len(published) == 1
    listing = published[0]
    assert listing["property"]["monthly_rent"] == 130000
    assert listing["property"]["source_is_demo"] is False
    assert listing["property"]["verification_status"] == "unverified"
    assert [image["kind"] for image in listing["images"]] == ["owner_photo"]
    assert client.get(listing["images"][0]["url"]).content == TINY_PNG


def test_studio_does_not_ask_for_bedrooms(client: TestClient, mock_llm: MockLLMProvider) -> None:
    mock_llm.listing_rule = parse_listing

    first = chat(client, "Je loue mon studio meublé à Yaoundé, quartier Bastos, 90 000 FCFA, joignable au 690 00 00 00")

    assert first["submission"]["fields"]["bedrooms"] == 0
    assert first["submission"]["missing_fields"] == []


def test_owner_can_cancel_and_nothing_is_published(client: TestClient, mock_llm: MockLLMProvider) -> None:
    summary = describe_listing(client, mock_llm)

    cancelled = chat(client, "Finalement j'annule", summary["conversation_id"])

    assert cancelled["submission"]["status"] == "cancelled"
    assert client.get("/api/admin/submissions", headers=ADMIN).json() == []


def test_photo_upload_is_validated_and_owned(client: TestClient, mock_llm: MockLLMProvider) -> None:
    summary = describe_listing(client, mock_llm)
    url = f"/api/submissions/{summary['submission']['id']}/photos?room=salon"

    not_an_image = client.post(url, content=b"<html>", headers={"X-Conversation-Id": summary["conversation_id"]})
    too_big = client.post(url, content=TINY_PNG + b"\x00" * 2_000, headers={"X-Conversation-Id": summary["conversation_id"]})
    stranger = client.post(url, content=TINY_PNG, headers={"X-Conversation-Id": "une-autre-conversation"})

    assert not_an_image.status_code == 415
    assert too_big.status_code == 413
    assert stranger.status_code == 404


def test_admin_routes_require_the_token(client: TestClient) -> None:
    assert client.get("/api/admin/submissions").status_code == 401
    assert client.get("/api/admin/submissions", headers={"X-Admin-Token": "faux"}).status_code == 401


def test_visualize_generates_a_labelled_illustration_when_no_photo(
    client: TestClient, mock_llm: MockLLMProvider, image_provider: FakeImageProvider
) -> None:
    from tests.fakes import scripted_extractions

    mock_llm.extraction_rule = scripted_extractions({"intent": "search", "updates": {"city": "Yaoundé"}})
    first = chat(client, "Un logement à Yaoundé")

    shown = chat(client, "Montre-moi la douche du n°2", first["conversation_id"])

    assert shown["scout"]["intent"] == "listing.visualize"
    assert shown["scout"]["tool_plan"][-1] == "image_service.generate_illustration"
    assert [image["kind"] for image in shown["images"]] == ["ai_generated_illustration"]
    assert shown["images"][0]["room"] == "salle_de_bain"
    assert "ne représente pas le logement réel" in shown["reply"]
    assert "bathroom" in image_provider.prompts[0]
    assert client.get(shown["images"][0]["url"]).status_code == 200


def test_visualize_without_configuration_says_so(
    client: TestClient, mock_llm: MockLLMProvider, image_provider: FakeImageProvider
) -> None:
    from tests.fakes import scripted_extractions

    image_provider.configured = False
    mock_llm.extraction_rule = scripted_extractions({"intent": "search", "updates": {"city": "Douala"}})
    first = chat(client, "Un logement à Douala")

    shown = chat(client, "À quoi ressemble le salon du premier ?", first["conversation_id"])

    assert shown["images"] == []
    assert "n'est pas configurée" in shown["reply"]


def test_visualize_uses_sample_photo_without_generating_an_illustration(
    client: TestClient, mock_llm: MockLLMProvider, image_provider: FakeImageProvider,
    session: Session, tmp_path: Path,
) -> None:
    mock_llm.extraction_rule = scripted_extractions(
        {"intent": "search", "updates": {"city": "Douala", "max_rent": 35000}}
    )
    first = chat(client, "Un logement à Douala, 35 000 FCFA maximum")
    file_name, content_type = LocalImageStore(tmp_path, max_bytes=1_000).save(TINY_PNG)
    session.add(PropertyImage(
        property_id=first["results"][0]["property"]["id"],
        kind="sample_photo", room="facade", file_name=file_name,
        content_type=content_type, size_bytes=len(TINY_PNG),
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()

    shown = chat(client, "Montre-moi la façade du premier", first["conversation_id"])

    assert shown["scout"]["intent"] == "listing.visualize"
    assert [image["kind"] for image in shown["images"]] == ["sample_photo"]
    assert "Ce n'est pas une photo de ce logement" in shown["reply"]
    assert image_provider.prompts == []
    assert client.get(shown["images"][0]["url"]).content == TINY_PNG


def test_generate_endpoint_and_status(client: TestClient) -> None:
    status_before = client.get("/api/images/status").json()

    generated = client.post("/api/images/generate", json={"description": "Façade d'une villa moderne", "room": "facade"})

    assert status_before == {"available": True, "remaining_today": 2}
    assert generated.status_code == 200
    assert generated.json()["is_ai_generated"] is True
    assert client.get("/api/images/status").json()["remaining_today"] == 1


def test_owner_flow_still_works_without_scout_routing(client: TestClient, mock_llm: MockLLMProvider) -> None:
    from app.api.dependencies import get_settings
    from app.main import app
    from tests.conftest import make_test_settings

    app.dependency_overrides[get_settings] = lambda: make_test_settings(
        admin_token="admin-de-test", scout_routing_enabled=False
    )
    summary = describe_listing(client, mock_llm)

    assert summary["scout"]["intent"] == "listing.submit"
