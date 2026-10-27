"""Propositions d'annonces par les propriétaires et images des logements.

Revision ID: 0003_submissions_and_images
Revises: 0002_zetaris_listings_view
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_submissions_and_images"
down_revision: Union[str, None] = "0002_zetaris_listings_view"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listing_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("city", sa.String(80), nullable=True),
        sa.Column("neighborhood", sa.String(120), nullable=True),
        sa.Column("property_type", sa.String(40), nullable=True),
        sa.Column("monthly_rent", sa.Integer(), nullable=True),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("furnished", sa.Boolean(), nullable=True),
        sa.Column("water_available", sa.Boolean(), nullable=True),
        sa.Column("electricity_available", sa.Boolean(), nullable=True),
        sa.Column("location_description", sa.Text(), nullable=True),
        sa.Column("contact_information", sa.String(200), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "approved_property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'pending', 'approved', 'rejected', 'cancelled')",
            name="ck_submission_status",
        ),
        sa.CheckConstraint(
            "monthly_rent IS NULL OR monthly_rent >= 0", name="ck_submission_nonnegative_rent"
        ),
    )
    op.create_index("ix_listing_submissions_session_id", "listing_submissions", ["session_id"])
    op.create_index("ix_listing_submissions_status", "listing_submissions", ["status"])

    op.create_table(
        "property_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("listing_submissions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("room", sa.String(30), nullable=False),
        sa.Column("file_name", sa.String(80), nullable=False, unique=True),
        sa.Column("content_type", sa.String(40), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(40), nullable=True),
        sa.Column("model", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('owner_photo', 'ai_generated_illustration', 'ai_edited_photo')",
            name="ck_image_kind",
        ),
        sa.CheckConstraint(
            "room IN ('facade', 'salon', 'chambre', 'cuisine', 'salle_de_bain', 'autre')",
            name="ck_image_room",
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_image_positive_size"),
    )
    op.create_index("ix_property_images_property_id", "property_images", ["property_id"])
    op.create_index("ix_property_images_submission_id", "property_images", ["submission_id"])
    op.create_index("ix_property_images_kind", "property_images", ["kind"])
    op.create_index("ix_property_images_created_at", "property_images", ["created_at"])


def downgrade() -> None:
    op.drop_table("property_images")
    op.drop_table("listing_submissions")
