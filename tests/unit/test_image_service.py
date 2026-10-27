"""Service métier des images avec un fournisseur simulé : il ignore tout de Cloudflare."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.integrations.image_generation.base import ImageGenerationNotConfiguredError
from app.repositories.image_repository import ImageRepository
from app.services.image_service import DailyImageLimitReachedError, ImageService, build_illustration_prompt
from app.services.image_storage import ImageTooLargeError, InvalidImageFileError, LocalImageStore
from tests.fakes import TINY_PNG, FakeImageProvider

NOW = datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc)


def make_service(session: Session, tmp_path: Path, provider: FakeImageProvider, limit: int = 2) -> ImageService:
    store = LocalImageStore(tmp_path, max_bytes=1_000)
    return ImageService(provider, store, ImageRepository(session), daily_limit=limit, now=lambda: NOW)


def test_generated_illustration_is_saved_and_labelled_as_ai(session: Session, tmp_path: Path) -> None:
    provider = FakeImageProvider()

    image = make_service(session, tmp_path, provider).generate_illustration("Salon lumineux", "salon")

    assert image.kind == "ai_generated_illustration"
    assert image.is_ai_generated is True
    assert "générée par IA" in image.label
    assert "ne représente pas le logement réel" in image.caption
    saved_files = list(tmp_path.iterdir())
    assert len(saved_files) == 1 and saved_files[0].read_bytes() == TINY_PNG
    assert image.url == f"/api/images/{image.id}"


def test_owner_photo_is_never_labelled_as_ai(session: Session, tmp_path: Path) -> None:
    from app.models.submission import ListingSubmission

    submission = ListingSubmission(session_id="conv-1", status="draft")
    session.add(submission)
    session.flush()

    photo = make_service(session, tmp_path, FakeImageProvider()).add_owner_photo(submission.id, TINY_PNG, "salon")

    assert photo.kind == "owner_photo"
    assert photo.is_ai_generated is False
    assert photo.caption is None
    assert photo.label.startswith("Photo fournie par le propriétaire")


def test_daily_limit_blocks_the_third_generation(session: Session, tmp_path: Path) -> None:
    provider = FakeImageProvider()
    service = make_service(session, tmp_path, provider, limit=2)

    service.generate_illustration("Façade", "facade")
    service.generate_illustration("Cuisine", "cuisine")

    assert service.remaining_generations_today() == 0
    with pytest.raises(DailyImageLimitReachedError):
        service.generate_illustration("Salon", "salon")
    assert len(provider.prompts) == 2


def test_missing_configuration_is_explicit(session: Session, tmp_path: Path) -> None:
    service = make_service(session, tmp_path, FakeImageProvider(configured=False))

    assert service.generation_available is False
    with pytest.raises(ImageGenerationNotConfiguredError):
        service.generate_illustration("Salon", "salon")


def test_prompt_only_uses_known_facts() -> None:
    prompt = build_illustration_prompt("salle_de_bain", "Douche carrelée", None)

    assert "bathroom" in prompt
    assert "Douche carrelée" in prompt
    assert "no text" in prompt


def test_store_refuses_non_images_and_oversized_files(tmp_path: Path) -> None:
    store = LocalImageStore(tmp_path, max_bytes=100)

    with pytest.raises(InvalidImageFileError):
        store.save(b"<script>alert(1)</script>")
    with pytest.raises(ImageTooLargeError):
        store.save(TINY_PNG + b"\x00" * 200)
    assert list(tmp_path.iterdir()) == []


def test_store_never_reads_outside_its_directory(tmp_path: Path) -> None:
    store = LocalImageStore(tmp_path, max_bytes=1_000)
    file_name, content_type = store.save(TINY_PNG)

    assert content_type == "image/png"
    assert store.path_for(file_name) is not None
    assert store.path_for("../../etc/passwd") is None
    assert store.path_for("../" + file_name) is None


def test_owner_photos_are_described_and_guide_the_illustration(session: Session, tmp_path: Path) -> None:
    from app.models.image import PropertyImage
    from app.schemas.property import PropertyRead
    from tests.fakes import FakeImageDescriber

    provider, describer = FakeImageProvider(), FakeImageDescriber("Murs jaunes, sol carrelé blanc.")
    store = LocalImageStore(tmp_path, max_bytes=1_000)
    service = ImageService(
        provider, store, ImageRepository(session), daily_limit=2, now=lambda: NOW, describer=describer
    )
    file_name, _ = store.save(TINY_PNG)
    session.add(PropertyImage(property_id=1, kind="owner_photo", room="salon", file_name=file_name,
                              content_type="image/png", size_bytes=len(TINY_PNG), created_at=NOW))
    session.flush()
    listing = PropertyRead.model_validate({
        "id": 1, "title": "Villa", "description": "Villa avec jardin", "city": "Douala",
        "neighborhood": "Bonapriso", "property_type": "villa", "monthly_rent": 300000, "currency": "XAF",
        "bedrooms": 4, "bathrooms": None, "furnished": None, "water_available": None,
        "electricity_available": None, "location_description": None, "latitude": None, "longitude": None,
        "source_name": "Test", "source_url": None, "contact_information": None, "listing_status": "unconfirmed",
        "verification_status": "unverified", "source_is_demo": True, "last_seen_at": None,
    })

    illustration = service.generate_illustration("Villa avec jardin", "facade", listing)

    assert illustration.reference_photo_count == 1
    assert describer.received_sizes == [len(TINY_PNG)]
    assert "Visible on the owner's real photos of this home: Murs jaunes, sol carrelé blanc." in provider.prompts[0]
    assert "a villa in Douala" in provider.prompts[0]
    assert "Listing description: Villa avec jardin" in provider.prompts[0]
    # Deuxième demande pour la même pièce : l'illustration existante est réutilisée.
    assert service.existing_illustration(1, "facade").id == illustration.id
    assert service.existing_illustration(1, "salon") is None


def test_without_vision_the_illustration_uses_text_only(session: Session, tmp_path: Path) -> None:
    provider = FakeImageProvider()

    image = make_service(session, tmp_path, provider).generate_illustration("Salon", "salon")

    assert image.reference_photo_count == 0
    assert "Visible on the owner's real photos" not in provider.prompts[0]


def test_prompt_is_anchored_in_cameroonian_housing() -> None:
    exterior = build_illustration_prompt("facade", "Maison avec cour", None)
    interior = build_illustration_prompt("cuisine", "Cuisine carrelée", None)

    assert "urban Cameroon" in exterior and "corrugated metal" in exterior
    assert "Not a European or North American house" in exterior
    assert "ceramic floor tiles" in interior and "corrugated metal" not in interior
    # La description réelle de l'annonce passe avant le contexte régional.
    assert exterior.index("Maison avec cour") < exterior.index("urban Cameroon")


def test_sample_photo_is_credited_and_guides_illustrations_when_no_owner_photo(
    session: Session, tmp_path: Path
) -> None:
    from tests.fakes import FakeImageDescriber

    provider, describer = FakeImageProvider(), FakeImageDescriber("Façade jaune, toit en tôle.")
    store = LocalImageStore(tmp_path, max_bytes=1_000)
    service = ImageService(provider, store, ImageRepository(session), daily_limit=2, now=lambda: NOW, describer=describer)

    sample = service.add_sample_photo(
        3, TINY_PNG, "facade", "Auteur Exemple", "CC BY-SA 4.0", "https://commons.wikimedia.org/wiki/File:X.jpg"
    )

    assert sample.kind == "sample_photo"
    assert sample.is_ai_generated is False
    assert "ne montre pas ce logement" in sample.label
    assert sample.credit == "Auteur Exemple · CC BY-SA 4.0 · Wikimedia Commons"
    # Une photo d'exemple n'est jamais présentée comme une photo du propriétaire.
    assert service.owner_photos(3) == []

    from app.repositories.property_repository import PropertyRepository
    from app.integrations.data.postgres import property_to_read

    listing = property_to_read(PropertyRepository(session).get_visible(3))
    illustration = service.generate_illustration("Appartement", "cuisine", listing)

    assert illustration.reference_photo_kind == "sample_photo"
    assert "Inspired by reference photos of similar homes in Cameroon: Façade jaune, toit en tôle." in provider.prompts[0]
    assert "owner's real photos" not in provider.prompts[0]
