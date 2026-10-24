"""Modèles SQLAlchemy des logements et de leurs sources."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PropertySource(Base):
    __tablename__ = "property_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    terms_url: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    properties: Mapped[list["Property"]] = relationship(back_populates="source")


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("source_id", "source_property_id", name="uq_property_source_ref"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("property_sources.id"), nullable=False, index=True
    )
    source_property_id: Mapped[str | None] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    neighborhood: Mapped[str | None] = mapped_column(String(120), index=True)
    property_type: Mapped[str] = mapped_column(String(40), nullable=False)
    monthly_rent: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="XAF", nullable=False)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[int | None] = mapped_column(Integer)
    furnished: Mapped[bool | None] = mapped_column(Boolean)
    water_available: Mapped[bool | None] = mapped_column(Boolean)
    electricity_available: Mapped[bool | None] = mapped_column(Boolean)
    location_description: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    source_url: Mapped[str | None] = mapped_column(Text)
    contact_information: Mapped[str | None] = mapped_column(String(200))
    listing_status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(30), default="unverified", nullable=False
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    source: Mapped[PropertySource] = relationship(back_populates="properties")
