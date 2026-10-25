"""Source d'annonces lue directement dans la base PostgreSQL de l'application."""

from app.models.property import Property
from app.repositories.property_repository import PropertyRepository
from app.schemas.criteria import SearchCriteria
from app.schemas.property import DataSourceName, PropertyRead


def property_to_read(property_record: Property) -> PropertyRead:
    return PropertyRead(
        id=property_record.id,
        title=property_record.title,
        description=property_record.description,
        city=property_record.city,
        neighborhood=property_record.neighborhood,
        property_type=property_record.property_type,
        monthly_rent=property_record.monthly_rent,
        currency=property_record.currency,
        bedrooms=property_record.bedrooms,
        bathrooms=property_record.bathrooms,
        furnished=property_record.furnished,
        water_available=property_record.water_available,
        electricity_available=property_record.electricity_available,
        location_description=property_record.location_description,
        latitude=property_record.latitude,
        longitude=property_record.longitude,
        source_name=property_record.source.name,
        source_url=property_record.source_url,
        contact_information=property_record.contact_information,
        listing_status=property_record.listing_status,
        verification_status=property_record.verification_status,
        source_is_demo=property_record.source.is_demo,
        last_seen_at=property_record.last_seen_at,
    )


class PostgresListingSource:
    name: DataSourceName = "postgres"

    def __init__(self, repository: PropertyRepository) -> None:
        self.repository = repository

    def find_candidates(self, criteria: SearchCriteria) -> list[PropertyRead]:
        return [property_to_read(item) for item in self.repository.find_candidates(criteria)]

    def get_property(self, property_id: int) -> PropertyRead | None:
        property_record = self.repository.get_visible(property_id)
        return property_to_read(property_record) if property_record else None
