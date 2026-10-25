"""Recherche déterministe et classement explicable des logements."""

from app.models.property import Property
from app.repositories.property_repository import PropertyRepository
from app.schemas.chat import SearchCriteria
from app.schemas.property import PropertyRead, PropertySearchResult


class SearchService:
    def __init__(self, repository: PropertyRepository) -> None:
        self.repository = repository

    def search(
        self, criteria: SearchCriteria, limit: int = 20
    ) -> tuple[list[PropertySearchResult], int]:
        properties, total = self.repository.search(criteria, limit)
        return [self._to_result(item, criteria) for item in properties], total

    def get_property(self, property_id: int) -> PropertyRead | None:
        property_record = self.repository.get_visible(property_id)
        return self._to_read(property_record) if property_record else None

    def _to_result(
        self, property_record: Property, criteria: SearchCriteria
    ) -> PropertySearchResult:
        reasons: list[str] = []
        if criteria.city:
            reasons.append(f"Situé à {property_record.city}.")
        if criteria.min_rent is not None or criteria.max_rent is not None:
            reasons.append("Le loyer respecte la fourchette demandée.")
        if criteria.bedrooms is not None:
            reasons.append(f"Le logement propose {property_record.bedrooms} chambre(s).")
        if criteria.water_available is not None:
            value = "disponible" if criteria.water_available else "indisponible"
            reasons.append(f"L’eau est indiquée comme {value}, comme demandé.")
        if criteria.electricity_available is not None:
            value = "disponible" if criteria.electricity_available else "indisponible"
            reasons.append(f"L’électricité est indiquée comme {value}, comme demandé.")
        if criteria.furnished is not None:
            value = "meublé" if criteria.furnished else "non meublé"
            reasons.append(f"Le logement est indiqué comme {value}, comme demandé.")
        if criteria.neighborhood and property_record.neighborhood:
            if criteria.neighborhood.casefold() in property_record.neighborhood.casefold():
                reasons.append(f"Le quartier correspond à « {criteria.neighborhood} ».")
            else:
                reasons.append(
                    f"Le logement est à {property_record.neighborhood}, "
                    f"pas au quartier demandé « {criteria.neighborhood} »."
                )
        if property_record.source.is_demo:
            reasons.append("Annonce fictive de démonstration.")

        missing_information = [
            label
            for value, label in (
                (property_record.bedrooms, "Nombre de chambres"),
                (property_record.bathrooms, "Nombre de salles de bain"),
                (property_record.furnished, "Logement meublé"),
                (property_record.water_available, "Disponibilité de l’eau"),
                (property_record.electricity_available, "Disponibilité de l’électricité"),
                (property_record.last_seen_at, "Date de dernière observation"),
                (property_record.neighborhood, "Quartier"),
            )
            if value is None
        ]

        return PropertySearchResult(
            property=self._to_read(property_record),
            reasons=reasons,
            missing_information=missing_information,
        )

    @staticmethod
    def _to_read(property_record: Property) -> PropertyRead:
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
