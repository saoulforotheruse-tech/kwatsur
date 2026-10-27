"""Contrats d'entrée et de sortie des images de logement."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ImageKind = Literal["owner_photo", "ai_generated_illustration", "ai_edited_photo"]
RoomType = Literal["facade", "salon", "chambre", "cuisine", "salle_de_bain", "autre"]

ROOM_LABELS: dict[str, str] = {
    "facade": "façade",
    "salon": "salon",
    "chambre": "chambre",
    "cuisine": "cuisine",
    "salle_de_bain": "salle de bain",
    "autre": "autre vue",
}

# Libellé toujours affiché avec l'image : une illustration IA n'est jamais présentée comme une photo.
KIND_LABELS: dict[str, str] = {
    "owner_photo": "Photo fournie par le propriétaire",
    "ai_generated_illustration": "Image illustrative générée par IA",
    "ai_edited_photo": "Photo réelle retouchée par IA",
}
AI_DISCLAIMER = (
    "Image illustrative générée par IA à partir d'une description : elle ne représente "
    "pas le logement réel."
)


class ImageRead(BaseModel):
    id: int
    url: str
    kind: ImageKind
    room: RoomType
    label: str
    is_ai_generated: bool
    caption: str | None = None
    property_id: int | None = None
    created_at: datetime


class GenerateImageRequest(BaseModel):
    """Demande d'illustration depuis l'interface (« Générer une image »)."""

    description: str = Field(min_length=3, max_length=600)
    room: RoomType = "facade"
    property_id: int | None = Field(default=None, ge=1)
