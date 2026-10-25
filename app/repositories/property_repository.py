"""Requêtes de persistance des logements."""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.property import Property
from app.schemas.chat import SearchCriteria


class PropertyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self, criteria: SearchCriteria, limit: int
    ) -> tuple[list[Property], int]:
        statement = (
            select(Property)
            .options(joinedload(Property.source))
            .join(Property.source)
            .where(Property.listing_status != "withdrawn")
        )
        count_statement = (
            select(func.count(Property.id))
            .join(Property.source)
            .where(Property.listing_status != "withdrawn")
        )

        filters = []
        if criteria.city:
            filters.append(func.lower(Property.city) == criteria.city.strip().lower())
        if criteria.min_rent is not None:
            filters.append(Property.monthly_rent >= criteria.min_rent)
        if criteria.max_rent is not None:
            filters.append(Property.monthly_rent <= criteria.max_rent)
        if criteria.bedrooms is not None:
            filters.append(Property.bedrooms == criteria.bedrooms)
        if criteria.water_available is not None:
            filters.append(Property.water_available.is_(criteria.water_available))
        if criteria.electricity_available is not None:
            filters.append(
                Property.electricity_available.is_(criteria.electricity_available)
            )
        if criteria.furnished is not None:
            filters.append(Property.furnished.is_(criteria.furnished))

        for condition in filters:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        if criteria.neighborhood:
            neighborhood_match = func.lower(Property.neighborhood).contains(
                criteria.neighborhood.strip().lower(), autoescape=True
            )
            statement = statement.order_by(case((neighborhood_match, 0), else_=1))
        known_details = sum(
            (
                case((column.is_not(None), 1), else_=0)
                for column in (
                    Property.bedrooms,
                    Property.bathrooms,
                    Property.furnished,
                    Property.water_available,
                    Property.electricity_available,
                )
            )
        )
        statement = statement.order_by(
            known_details.desc(), Property.monthly_rent, Property.id
        )
        properties = list(self.session.scalars(statement.limit(limit)))
        total = self.session.scalar(count_statement) or 0
        return properties, total

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
