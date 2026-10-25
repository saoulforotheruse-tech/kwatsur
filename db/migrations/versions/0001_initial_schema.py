"""Création du schéma initial Kwatsur.

Revision ID: 0001_initial_schema
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "property_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("terms_url", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("source_property_id", sa.String(120), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("neighborhood", sa.String(120), nullable=True),
        sa.Column("property_type", sa.String(40), nullable=False),
        sa.Column("monthly_rent", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="XAF"),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("furnished", sa.Boolean(), nullable=True),
        sa.Column("water_available", sa.Boolean(), nullable=True),
        sa.Column("electricity_available", sa.Boolean(), nullable=True),
        sa.Column("location_description", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("contact_information", sa.String(200), nullable=True),
        sa.Column(
            "listing_status", sa.String(30), nullable=False, server_default="unconfirmed"
        ),
        sa.Column(
            "verification_status", sa.String(30), nullable=False, server_default="unverified"
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["source_id"], ["property_sources.id"]),
        sa.UniqueConstraint("source_id", "source_property_id", name="uq_property_source_ref"),
        sa.CheckConstraint("monthly_rent >= 0", name="ck_property_nonnegative_rent"),
        sa.CheckConstraint(
            "bedrooms IS NULL OR bedrooms >= 0", name="ck_property_nonnegative_bedrooms"
        ),
        sa.CheckConstraint(
            "bathrooms IS NULL OR bathrooms >= 0", name="ck_property_nonnegative_bathrooms"
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="ck_property_latitude_range",
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="ck_property_longitude_range",
        ),
    )
    op.create_index("ix_properties_source_id", "properties", ["source_id"])
    op.create_index("ix_properties_source_property_id", "properties", ["source_property_id"])
    op.create_index("ix_properties_city", "properties", ["city"])
    op.create_index("ix_properties_neighborhood", "properties", ["neighborhood"])
    op.create_index("ix_properties_monthly_rent", "properties", ["monthly_rent"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "search_criteria",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_index("ix_properties_monthly_rent", table_name="properties")
    op.drop_index("ix_properties_neighborhood", table_name="properties")
    op.drop_index("ix_properties_city", table_name="properties")
    op.drop_index("ix_properties_source_property_id", table_name="properties")
    op.drop_index("ix_properties_source_id", table_name="properties")
    op.drop_table("properties")
    op.drop_table("property_sources")
