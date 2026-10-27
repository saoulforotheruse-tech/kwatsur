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
