"""Vue plate des annonces, exposée à Zetaris comme source PostgreSQL.

Revision ID: 0002_zetaris_listings_view
Revises: 0001_initial_schema

Colonnes identiques à LISTING_COLUMNS (app/integrations/data/zetaris.py). Zetaris lit
cette vue avec un rôle en lecture seule (voir docs/sponsor-tech.md).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002_zetaris_listings_view"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIEW zetaris_listings AS
        SELECT p.id, p.title, p.description, p.city, p.neighborhood, p.property_type,
               p.monthly_rent, p.currency, p.bedrooms, p.bathrooms, p.furnished,
               p.water_available, p.electricity_available, p.location_description,
               p.latitude, p.longitude, s.name AS source_name, p.source_url,
               p.contact_information, p.listing_status, p.verification_status,
               s.is_demo AS source_is_demo, p.last_seen_at
        FROM properties p
        JOIN property_sources s ON s.id = p.source_id
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS zetaris_listings")
