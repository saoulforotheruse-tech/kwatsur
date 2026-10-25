"""Insère des annonces fictives pour tester la recherche locale."""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.property import Property, PropertySource

DEMO_SOURCE_NAME = "Données fictives Kwatsur"

DEMO_PROPERTIES = (
    {
        "source_property_id": "demo-yaounde-melen-studio",
        "title": "Studio de démonstration à Melen",
        "description": "Exemple fictif pour tester les filtres de recherche.",
        "city": "Yaoundé",
        "neighborhood": "Melen",
        "property_type": "studio",
        "monthly_rent": 90000,
        "bedrooms": 0,
        "bathrooms": None,
        "furnished": None,
        "water_available": None,
        "electricity_available": True,
        "listing_status": "unconfirmed",
    },
    {
        "source_property_id": "demo-douala-bonamoussadi-two-bedrooms",
        "title": "Appartement de démonstration à Bonamoussadi",
        "description": "Exemple fictif pour tester les filtres et équipements.",
        "city": "Douala",
        "neighborhood": "Bonamoussadi",
        "property_type": "appartement",
        "monthly_rent": 120000,
        "bedrooms": 2,
        "bathrooms": 1,
        "furnished": False,
        "water_available": True,
        "electricity_available": True,
        "listing_status": "unconfirmed",
    },
    {
        "source_property_id": "demo-douala-bonapriso-studio",
        "title": "Studio de démonstration à Bonapriso",
        "description": "Exemple fictif dont le loyer dépasse certains budgets.",
        "city": "Douala",
        "neighborhood": "Bonapriso",
        "property_type": "studio",
        "monthly_rent": 150000,
        "bedrooms": 0,
        "bathrooms": 1,
        "furnished": True,
        "water_available": True,
        "electricity_available": None,
        "listing_status": "unconfirmed",
    },
)


def seed_demo_properties() -> int:
    with SessionLocal.begin() as session:
        source = session.scalar(
            select(PropertySource).where(PropertySource.name == DEMO_SOURCE_NAME)
        )
        if source is None:
            source = PropertySource(
                name=DEMO_SOURCE_NAME,
                source_type="demo",
                is_demo=True,
            )
            session.add(source)
            session.flush()

        inserted = 0
        for property_data in DEMO_PROPERTIES:
            existing = session.scalar(
                select(Property.id).where(
                    Property.source_id == source.id,
                    Property.source_property_id == property_data["source_property_id"],
                )
            )
            if existing is None:
                session.add(Property(source_id=source.id, **property_data))
                inserted += 1
        return inserted


if __name__ == "__main__":
    added = seed_demo_properties()
    print(f"{added} annonce(s) fictive(s) ajoutée(s).")
