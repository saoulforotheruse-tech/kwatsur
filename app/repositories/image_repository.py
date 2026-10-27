"""Requêtes de persistance des métadonnées d'image (les fichiers sont sur le disque)."""

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.image import PropertyImage

AI_KINDS = ("ai_generated_illustration", "ai_edited_photo")


class ImageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, image: PropertyImage) -> PropertyImage:
        self.session.add(image)
        self.session.flush()
        return image

    def get(self, image_id: int) -> PropertyImage | None:
        return self.session.get(PropertyImage, image_id)

    def for_properties(self, property_ids: list[int]) -> list[PropertyImage]:
        if not property_ids:
            return []
        statement = (
            select(PropertyImage)
            .where(PropertyImage.property_id.in_(property_ids))
            .order_by(PropertyImage.property_id, PropertyImage.kind, PropertyImage.id)
        )
        return list(self.session.scalars(statement))

    def for_submission(self, submission_id: int) -> list[PropertyImage]:
        statement = (
            select(PropertyImage)
            .where(PropertyImage.submission_id == submission_id)
            .order_by(PropertyImage.id)
        )
        return list(self.session.scalars(statement))

    def count_ai_generated_since(self, since: datetime) -> int:
        """Images IA enregistrées depuis `since` : base de la limite quotidienne de Kwatsur."""
        statement = select(func.count(PropertyImage.id)).where(
            PropertyImage.kind.in_(AI_KINDS), PropertyImage.created_at >= since
        )
        return int(self.session.scalar(statement) or 0)

    def attach_submission_to_property(self, submission_id: int, property_id: int) -> None:
        """À l'approbation, les photos de la proposition suivent le logement publié."""
        self.session.execute(
            update(PropertyImage)
            .where(PropertyImage.submission_id == submission_id)
            .values(property_id=property_id)
        )

    def commit(self) -> None:
        self.session.commit()
