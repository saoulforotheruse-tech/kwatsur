"""Contrat commun des sources d'annonces (PostgreSQL, Zetaris, futurs partenaires)."""

from typing import Protocol

from app.schemas.criteria import SearchCriteria
from app.schemas.property import DataSourceName, PropertyRead


class ListingSource(Protocol):
    name: DataSourceName

    def find_candidates(self, criteria: SearchCriteria) -> list[PropertyRead]:
        """Annonces susceptibles de convenir ; le filtrage final reste fait par le backend."""
        ...

    def get_property(self, property_id: int) -> PropertyRead | None: ...
