"""Modèle SQLAlchemy des images d'un logement.

Le fichier est sur le disque (dossier MEDIA_DIRECTORY) ; la base ne garde que ses métadonnées.
`kind` distingue toujours une vraie photo d'une image produite par l'IA :
- owner_photo : photographie envoyée par le propriétaire ;
- ai_generated_illustration : image illustrative générée par l'IA, jamais une photo du logement ;
- ai_edited_photo : réservé à une future retouche IA d'une vraie photo.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

IMAGE_KINDS = ("owner_photo", "ai_generated_illustration", "ai_edited_photo")
ROOM_TYPES = ("facade", "salon", "chambre", "cuisine", "salle_de_bain", "autre")


class PropertyImage(Base):
    __tablename__ = "property_images"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('owner_photo', 'ai_generated_illustration', 'ai_edited_photo')",
            name="ck_image_kind",
        ),
        CheckConstraint(
            "room IN ('facade', 'salon', 'chambre', 'cuisine', 'salle_de_bain', 'autre')",
            name="ck_image_room",
        ),
        CheckConstraint("size_bytes > 0", name="ck_image_positive_size"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Une image est rattachée à un logement publié, à une proposition en attente, ou à rien
    # (illustration libre demandée depuis l'interface).
    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True
    )
    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("listing_submissions.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    room: Mapped[str] = mapped_column(String(30), nullable=False)
    # Nom généré par Kwatsur (UUID + extension), jamais celui fourni par l'utilisateur.
    file_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Renseignés seulement pour une image générée : la description envoyée et qui l'a produite.
    prompt: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
