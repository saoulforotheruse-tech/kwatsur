"""Exporte les annonces PostgreSQL en CSV, au format attendu par l'adaptateur Zetaris.

Usage : python -m scripts.export_listings_csv data/kwatsur_listings.csv
Le fichier est ensuite importé dans Zetaris (NDP File System → file-store), puis enregistré
comme table ; son nom complet va dans ZETARIS_LISTINGS_TABLE.
"""

import csv
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.integrations.data.postgres import property_to_read
from app.integrations.data.zetaris import LISTING_COLUMNS
from app.models.property import Property


def export_listings(output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as session, output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=LISTING_COLUMNS)
        writer.writeheader()
        statement = select(Property).options(joinedload(Property.source)).order_by(Property.id)
        count = 0
        for property_record in session.scalars(statement):
            row = property_to_read(property_record).model_dump(mode="json")
            # Valeur inconnue = cellule vide (jamais « false » par défaut).
            writer.writerow({column: "" if row[column] is None else row[column] for column in LISTING_COLUMNS})
            count += 1
    return count


if __name__ == "__main__":
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "data/kwatsur_listings.csv")
    exported = export_listings(destination)
    print(f"{exported} annonce(s) exportée(s) vers {destination}.")
