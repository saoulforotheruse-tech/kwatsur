"""Requêtes de persistance des logements."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.property import Property
from app.schemas.criteria import SearchCriteria

# Plafond de candidats lus avant le classement en Python.
MAX_CANDIDATES = 300


class PropertyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_candidates(self, criteria: SearchCriteria) -> list[Property]:
        """Pré-filtre en SQL les critères obligatoires ; le classement se fait ailleurs."""
        statement = (
            select(Property)
            .options(joinedload(Property.source))
            .where(Property.listing_status != "withdrawn")
        )
        if criteria.city:
            statement = statement.where(func.lower(Property.city) == criteria.city.lower())
        if criteria.property_type:
            statement = statement.where(
                func.lower(Property.property_type) == criteria.property_type
            )
        if criteria.min_rent is not None:
            statement = statement.where(Property.monthly_rent >= criteria.min_rent)
        if criteria.max_rent is not None:
            statement = statement.where(Property.monthly_rent <= criteria.max_rent)
        if criteria.bedrooms is not None:
            statement = statement.where(
                or_(Property.bedrooms.is_(None), Property.bedrooms >= criteria.bedrooms)
            )

        # Un équipement exigé n'exclut que les annonces qui le déclarent absent :
        # une valeur inconnue reste candidate et sera signalée « à vérifier ».
        for required, column in (
            (criteria.water_available, Property.water_available),
            (criteria.electricity_available, Property.electricity_available),
        ):
            if required:
                statement = statement.where(or_(column.is_(None), column.is_(True)))
        if criteria.furnished is not None:
            statement = statement.where(
                or_(Property.furnished.is_(None), Property.furnished.is_(criteria.furnished))
            )

        statement = statement.order_by(Property.id).limit(MAX_CANDIDATES)
        return list(self.session.scalars(statement).unique())

    def get_visible(self, property_id: int) -> Property | None:
        statement = (
            select(Property)
            .options(joinedload(Property.source))
            .where(
                Property.id == property_id,
                Property.listing_status != "withdrawn",
            )
        )
        return self.session.scalar(statement)
