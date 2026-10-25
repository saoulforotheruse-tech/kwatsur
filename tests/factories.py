"""Construction rapide d'annonces normalisées pour les tests unitaires."""

from datetime import datetime, timezone
from itertools import count

from app.schemas.property import PropertyRead

_ids = count(1)


def make_listing(**overrides: object) -> PropertyRead:
    values: dict[str, object] = {
        "id": next(_ids),
        "title": "Appartement test",
        "description": None,
        "city": "Douala",
        "neighborhood": "Bonamoussadi",
        "property_type": "appartement",
        "monthly_rent": 120000,
        "currency": "XAF",
        "bedrooms": 2,
        "bathrooms": 1,
        "furnished": False,
        "water_available": True,
        "electricity_available": True,
        "location_description": None,
        "latitude": None,
        "longitude": None,
        "source_name": "Données fictives",
        "source_url": None,
        "contact_information": None,
        "listing_status": "unconfirmed",
        "verification_status": "unverified",
        "source_is_demo": True,
        "last_seen_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return PropertyRead(**values)
