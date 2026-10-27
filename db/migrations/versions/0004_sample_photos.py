"""Photos d'exemple sous licence libre (crédit obligatoire) pour les annonces de démonstration.

Revision ID: 0004_sample_photos
Revises: 0003_submissions_and_images
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_sample_photos"
down_revision: Union[str, None] = "0003_submissions_and_images"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_KINDS = "kind IN ('owner_photo', 'ai_generated_illustration', 'ai_edited_photo')"
NEW_KINDS = "kind IN ('owner_photo', 'sample_photo', 'ai_generated_illustration', 'ai_edited_photo')"


def upgrade() -> None:
    op.add_column("property_images", sa.Column("author", sa.String(200), nullable=True))
    op.add_column("property_images", sa.Column("license", sa.String(60), nullable=True))
    op.add_column("property_images", sa.Column("source_url", sa.Text(), nullable=True))
    op.drop_constraint("ck_image_kind", "property_images", type_="check")
    op.create_check_constraint("ck_image_kind", "property_images", NEW_KINDS)


def downgrade() -> None:
    op.execute("DELETE FROM property_images WHERE kind = 'sample_photo'")
    op.drop_constraint("ck_image_kind", "property_images", type_="check")
    op.create_check_constraint("ck_image_kind", "property_images", OLD_KINDS)
    op.drop_column("property_images", "source_url")
    op.drop_column("property_images", "license")
    op.drop_column("property_images", "author")
