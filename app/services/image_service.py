"""Logique métier des images de Kwatsur : photos des propriétaires et illustrations IA.

Parcours d'une illustration :
  description + pièce → contrôle de la limite quotidienne de Kwatsur → prompt
  → fournisseur (interface ImageGenerationProvider) → vérification et écriture du fichier
  → métadonnées en base avec kind="ai_generated_illustration".
Ce service ne connaît aucun fournisseur précis : Cloudflare n'est qu'une implémentation.
"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from app.core.exceptions import KwatsurError
from app.integrations.image_generation.base import ImageGenerationProvider
from app.models.image import PropertyImage
from app.repositories.image_repository import ImageRepository
from app.schemas.image import AI_DISCLAIMER, KIND_LABELS, ROOM_LABELS, ImageRead
from app.schemas.property import PropertyRead, PropertySearchResult
from app.services.image_storage import LocalImageStore

logger = logging.getLogger(__name__)

# Vocabulaire anglais : les modèles d'image comprennent mieux l'anglais que le français.
ROOM_PROMPTS = {
    "facade": "exterior front view of the house",
    "salon": "living room interior",
    "chambre": "bedroom interior",
    "cuisine": "kitchen interior",
    "salle_de_bain": "bathroom with shower, interior",
    "autre": "view",
}


class DailyImageLimitReachedError(KwatsurError):
    status_code = 429
    public_message = "La limite quotidienne d'images de Kwatsur est atteinte. Réessayez demain."


def build_illustration_prompt(room: str, description: str, listing: PropertyRead | None) -> str:
    """Prompt envoyé au modèle : uniquement des faits connus, jamais d'information inventée."""
    parts = [f"Realistic architectural illustration, {ROOM_PROMPTS[room]}"]
    if listing is not None:
        parts.append(f"of a {listing.property_type} in {listing.city}, Cameroon")
        if listing.bedrooms:
            parts.append(f"with {listing.bedrooms} bedroom(s)")
        if listing.furnished is True:
            parts.append("furnished")
    else:
        parts.append("of a home in Cameroon")
    parts.append(f"Description: {description.strip()}")
    parts.append("Natural daylight, simple and realistic, no text, no watermark, no people.")
    return ". ".join(parts)


def to_image_read(image: PropertyImage) -> ImageRead:
    is_ai = image.kind != "owner_photo"
    room_label = ROOM_LABELS.get(image.room, image.room)
    return ImageRead(
        id=image.id,
        url=f"/api/images/{image.id}",
        kind=image.kind,
        room=image.room,
        label=f"{KIND_LABELS[image.kind]} · {room_label}",
        is_ai_generated=is_ai,
        caption=AI_DISCLAIMER if is_ai else None,
        property_id=image.property_id,
        created_at=image.created_at,
    )


class ImageService:
    def __init__(
        self,
        provider: ImageGenerationProvider,
        store: LocalImageStore,
        repository: ImageRepository,
        daily_limit: int,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.provider = provider
        self.store = store
        self.repository = repository
        self.daily_limit = daily_limit
        self.now = now

    @property
    def generation_available(self) -> bool:
        return self.provider.is_configured

    def remaining_generations_today(self) -> int:
        start_of_day = self.now().replace(hour=0, minute=0, second=0, microsecond=0)
        used = self.repository.count_ai_generated_since(start_of_day)
        return max(0, self.daily_limit - used)

    def generate_illustration(
        self, description: str, room: str, listing: PropertyRead | None = None
    ) -> ImageRead:
        """Génère, enregistre et renvoie une illustration IA clairement étiquetée."""
        if not self.provider.is_configured:
            # Message explicite du fournisseur (variables manquantes ou génération désactivée).
            self.provider.generate_image(description)
        if self.remaining_generations_today() <= 0:
            raise DailyImageLimitReachedError(
                f"La limite de Kwatsur ({self.daily_limit} image(s) par jour) est atteinte. "
                "Réessayez demain (renouvellement à minuit UTC)."
            )

        prompt = build_illustration_prompt(room, description, listing)
        generated = self.provider.generate_image(prompt)
        file_name, content_type = self.store.save(generated.data)
        image = self.repository.add(
            PropertyImage(
                property_id=listing.id if listing is not None else None,
                kind="ai_generated_illustration",
                room=room,
                file_name=file_name,
                content_type=content_type,
                size_bytes=len(generated.data),
                prompt=prompt,
                provider=generated.provider,
                model=generated.model,
                created_at=self.now(),
            )
        )
        self.repository.commit()
        logger.info("Illustration générée (%s, %s) pour le logement %s", generated.provider, room, image.property_id)
        return to_image_read(image)

    def add_owner_photo(self, submission_id: int, image_bytes: bytes, room: str) -> ImageRead:
        """Enregistre une vraie photo envoyée par le propriétaire pour sa proposition."""
        file_name, content_type = self.store.save(image_bytes)
        image = self.repository.add(
            PropertyImage(
                submission_id=submission_id,
                kind="owner_photo",
                room=room,
                file_name=file_name,
                content_type=content_type,
                size_bytes=len(image_bytes),
                created_at=self.now(),
            )
        )
        self.repository.commit()
        return to_image_read(image)

    def owner_photos(self, property_id: int, room: str | None = None) -> list[ImageRead]:
        images = [
            image
            for image in self.repository.for_properties([property_id])
            if image.kind == "owner_photo" and (room is None or image.room == room)
        ]
        return [to_image_read(image) for image in images]

    def submission_images(self, submission_id: int) -> list[ImageRead]:
        return [to_image_read(image) for image in self.repository.for_submission(submission_id)]

    def attach_photos(self, results: list[PropertySearchResult]) -> list[PropertySearchResult]:
        """Ajoute aux résultats leurs images (photos d'abord, puis illustrations IA)."""
        images = self.repository.for_properties([result.property.id for result in results])
        by_property: dict[int, list[ImageRead]] = {}
        for image in sorted(images, key=lambda item: (item.kind != "owner_photo", item.id)):
            by_property.setdefault(image.property_id, []).append(to_image_read(image))
        for result in results:
            result.images = by_property.get(result.property.id, [])
        return results

    def file_for(self, image_id: int) -> tuple[str, str] | None:
        """(chemin du fichier, type MIME) d'une image connue, sinon None."""
        image = self.repository.get(image_id)
        if image is None:
            return None
        path = self.store.path_for(image.file_name)
        return (str(path), image.content_type) if path else None
