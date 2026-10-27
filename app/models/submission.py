"""Modèle SQLAlchemy d'une annonce proposée par un propriétaire dans le chat.

Une proposition n'est jamais visible des chercheurs tant qu'un administrateur ne l'a pas
approuvée : l'approbation crée alors une vraie ligne dans `properties`.
Cycle de vie : draft (en cours de description) → pending (envoyée) → approved / rejected,
ou cancelled si le propriétaire abandonne.
"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SUBMISSION_STATUSES = ("draft", "pending", "approved", "rejected", "cancelled")


class ListingSubmission(Base):
    __tablename__ = "listing_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending', 'approved', 'rejected', 'cancelled')",
            name="ck_submission_status",
        ),
        CheckConstraint(
            "monthly_rent IS NULL OR monthly_rent >= 0", name="ck_submission_nonnegative_rent"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Conversation d'où vient la proposition : seul son détenteur peut y ajouter des photos.
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)

    title: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(80))
    neighborhood: Mapped[str | None] = mapped_column(String(120))
    property_type: Mapped[str | None] = mapped_column(String(40))
    monthly_rent: Mapped[int | None] = mapped_column(Integer)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[int | None] = mapped_column(Integer)
    furnished: Mapped[bool | None] = mapped_column(Boolean)
    water_available: Mapped[bool | None] = mapped_column(Boolean)
    electricity_available: Mapped[bool | None] = mapped_column(Boolean)
    location_description: Mapped[str | None] = mapped_column(Text)
    contact_information: Mapped[str | None] = mapped_column(String(200))

    review_note: Mapped[str | None] = mapped_column(Text)
    approved_property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
