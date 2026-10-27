"""Logique métier des images de Kwatsur : photos des propriétaires et illustrations IA.

Parcours d'une illustration :
  description + pièce → contrôle de la limite quotidienne de Kwatsur
  → description des VRAIES photos du propriétaire par un modèle de vision (si disponibles)
  → prompt fait des seuls faits connus → fournisseur (interface ImageGenerationProvider)
  → vérification et écriture du fichier → métadonnées avec kind="ai_generated_illustration".
Une illustration déjà générée pour le même logement et la même pièce est réutilisée.
Ce service ne connaît aucun fournisseur précis : Cloudflare n'est qu'une implémentation.
"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from app.core.exceptions import KwatsurError
from app.integrations.image_description.base import DisabledImageDescriber, ImageDescriber
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

# Contexte régional : sans lui, le modèle dessine une maison européenne ou américaine.
# Ce sont des traits courants de l'habitat urbain camerounais, pas des faits sur l'annonce :
# la description réelle passe avant (elle est placée plus tôt dans le prompt).
CAMEROON_STYLE = {
    "exterior": (
        "Typical contemporary home of urban Cameroon (Central Africa, Douala or Yaoundé): "
        "rendered concrete-block walls painted in a light or bright colour, corrugated metal "
        "sheet or clay tile roof with overhanging eaves, louvered or barred windows, a perimeter "
        "wall with a painted metal gate, red laterite ground or paved courtyard, tropical plants "
        "such as banana trees and palms, humid tropical light."
    ),
    "interior": (
        "Typical interior of a home in urban Cameroon (Central Africa): plastered walls painted "
        "in light colours, glazed ceramic floor tiles, louvered or barred windows with simple "
        "curtains, ceiling fan, modest locally made furniture, tropical daylight."
    ),
}
CITY_SETTINGS = {
    "Douala": "Douala, a humid coastal port city in Cameroon",
    "Yaoundé": "Yaoundé, the hilly capital of Cameroon",
}
# Types de logement des annonces (français) → anglais, compris par le modèle d'image.
PROPERTY_TYPES_EN = {
    "maison": "house",
    "appartement": "apartment",
    "studio": "studio apartment",
    "chambre": "rented room",
    "villa": "villa",
    "duplex": "duplex house",
}
# Introduction de ce que montrent les photos décrites, selon leur origine.
REFERENCE_INTROS = {
    "owner_photo": "Visible on the owner's real photos of this home:",
    "sample_photo": "Inspired by reference photos of similar homes in Cameroon:",
}
NEGATIVE_STYLE = "Not a European or North American house, no snow, no fireplace, no suburban lawn."


# Question posée au modèle de vision pour chaque vraie photo (réponse courte, factuelle).
PHOTO_QUESTION = (
    "Describe only what is visible in this photo of a home: wall and floor colors, materials, "
    "roof, furniture and overall style. One or two short sentences, no guesses."
)


class DailyImageLimitReachedError(KwatsurError):
    status_code = 429
    public_message = "La limite quotidienne d'images de Kwatsur est atteinte. Réessayez demain."


def build_illustration_prompt(
    room: str,
    description: str,
    listing: PropertyRead | None,
    photo_details: list[str] | None = None,
    reference_kind: str | None = None,
) -> str:
    """Prompt envoyé au modèle : uniquement des faits connus, jamais d'information inventée."""
    place = CITY_SETTINGS.get(listing.city, f"{listing.city}, Cameroon") if listing else "Cameroon"
    kind = PROPERTY_TYPES_EN.get(listing.property_type, listing.property_type) if listing else "home"
    subject = f"a {kind} in {place}" if listing else "a home in Cameroon"
    features = []
    if listing is not None and listing.bedrooms:
        features.append(f"{listing.bedrooms} bedroom(s)")
    if listing is not None and listing.furnished is True:
        features.append("furnished")
    sentences = [
        f"Realistic architectural illustration of the {ROOM_PROMPTS[room]} of {subject}"
        + (f" ({', '.join(features)})" if features else "")
        + ".",
        f"Listing description: {description.strip()}",
    ]
    if photo_details:
        # Ce que montrent les vraies photos du propriétaire : à respecter (couleurs, matériaux).
        intro = REFERENCE_INTROS.get(reference_kind, REFERENCE_INTROS["owner_photo"])
        sentences.append(f"{intro} " + " ".join(photo_details))
    sentences.append(CAMEROON_STYLE["exterior" if room == "facade" else "interior"])
    sentences.append(NEGATIVE_STYLE)
    sentences.append("Photorealistic, natural light, no text, no watermark, no people.")
    return " ".join(sentences)


# Types d'image produits par l'IA (jamais présentés comme des photos).
AI_IMAGE_KINDS = ("ai_generated_illustration", "ai_edited_photo")
# Photos réelles utilisables comme référence par la vision, par ordre de préférence.
REFERENCE_PHOTO_KINDS = ("owner_photo", "sample_photo")


def photo_credit(image: PropertyImage) -> str | None:
    """« Auteur, licence, Wikimedia Commons » : crédit exigé par les licences CC BY-SA."""
    if image.kind != "sample_photo":
        return None
    parts = [part for part in (image.author, image.license) if part]
    return " · ".join([*parts, "Wikimedia Commons"]) if parts else "Wikimedia Commons"


def to_image_read(image: PropertyImage) -> ImageRead:
    is_ai = image.kind in AI_IMAGE_KINDS
    room_label = ROOM_LABELS.get(image.room, image.room)
    credit = photo_credit(image)
    caption = AI_DISCLAIMER if is_ai else None
    if image.kind == "sample_photo":
        caption = f"Photo d'exemple d'un logement au Cameroun, elle ne montre pas ce logement. Crédit : {credit}."
    return ImageRead(
        id=image.id,
        url=f"/api/images/{image.id}",
        kind=image.kind,
        room=image.room,
        label=f"{KIND_LABELS[image.kind]} · {room_label}",
        is_ai_generated=is_ai,
        caption=caption,
        property_id=image.property_id,
        credit=credit,
        source_url=image.source_url,
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
        describer: ImageDescriber | None = None,
        max_reference_photos: int = 2,
        max_reference_photo_bytes: int = 1_500_000,
    ) -> None:
        self.provider = provider
        self.store = store
        self.repository = repository
        self.daily_limit = daily_limit
        self.now = now
        self.describer = describer or DisabledImageDescriber()
        self.max_reference_photos = max_reference_photos
        self.max_reference_photo_bytes = max_reference_photo_bytes

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

        photo_details, reference_kind = (
            self._describe_reference_photos(listing.id) if listing is not None else ([], None)
        )
        prompt = build_illustration_prompt(room, description, listing, photo_details, reference_kind)
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
        logger.info(
            "Illustration générée (%s, %s) pour le logement %s, %s photo(s) réelle(s) décrite(s)",
            generated.provider, room, image.property_id, len(photo_details),
        )
        illustration = to_image_read(image)
        illustration.reference_photo_count = len(photo_details)
        illustration.reference_photo_kind = reference_kind if photo_details else None
        return illustration

    def existing_illustration(self, property_id: int, room: str) -> ImageRead | None:
        """Illustration déjà générée pour ce logement et cette pièce : réutilisée sans quota."""
        illustrations = [
            image
            for image in self.repository.for_properties([property_id])
            if image.kind == "ai_generated_illustration" and image.room == room
        ]
        return to_image_read(illustrations[-1]) if illustrations else None

    def _describe_reference_photos(self, property_id: int) -> tuple[list[str], str | None]:
        """Fait décrire quelques photos réelles : celles du propriétaire, sinon les photos d'exemple.

        Jamais une illustration IA. Un échec de la vision n'empêche pas l'illustration.
        """
        if not self.describer.is_configured or self.max_reference_photos == 0:
            return [], None
        images = self.repository.for_properties([property_id])
        for reference_kind in REFERENCE_PHOTO_KINDS:
            photos = [
                image
                for image in images
                if image.kind == reference_kind and image.size_bytes <= self.max_reference_photo_bytes
            ][: self.max_reference_photos]
            if photos:
                return self._describe(photos), reference_kind
        return [], None

    def _describe(self, photos: list[PropertyImage]) -> list[str]:
        details: list[str] = []
        for photo in photos:
            path = self.store.path_for(photo.file_name)
            if path is None:
                continue
            try:
                details.append(self.describer.describe(path.read_bytes(), PHOTO_QUESTION))
            except (KwatsurError, OSError) as error:
                logger.warning("Photo %s non décrite : %s", photo.id, getattr(error, "public_message", error))
        return details

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

    def add_sample_photo(
        self, property_id: int, image_bytes: bytes, room: str, author: str, license_name: str, source_url: str
    ) -> ImageRead:
        """Rattache une photo d'exemple sous licence libre à une annonce de démonstration."""
        file_name, content_type = self.store.save(image_bytes)
        image = self.repository.add(
            PropertyImage(
                property_id=property_id,
                kind="sample_photo",
                room=room,
                file_name=file_name,
                content_type=content_type,
                size_bytes=len(image_bytes),
                author=author,
                license=license_name,
                source_url=source_url,
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
        """Ajoute aux résultats leurs images : photos du propriétaire, d'exemple, puis illustrations IA."""
        images = self.repository.for_properties([result.property.id for result in results])
        display_order = {"owner_photo": 0, "sample_photo": 1}
        by_property: dict[int, list[ImageRead]] = {}
        for image in sorted(images, key=lambda item: (display_order.get(item.kind, 2), item.id)):
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
