"""Recherche déterministe : source d'annonces → filtres obligatoires → classement → risques."""

import logging
from dataclasses import dataclass, field

from app.core.exceptions import KwatsurError
from app.integrations.data.base import ListingSource
from app.schemas.criteria import SearchCriteria, normalize_text
from app.schemas.property import DataSourceName, PropertyRead, PropertySearchResult
from app.services.ranking_service import RankingService
from app.services.risk_service import RiskService, missing_information

logger = logging.getLogger(__name__)


def satisfies_mandatory_criteria(listing: PropertyRead, criteria: SearchCriteria) -> bool:
    """Filtre appliqué en Python à toutes les sources, quel que soit leur pré-filtrage.

    Une donnée inconnue ne fait pas échouer un critère : seule une valeur contraire exclut.
    """
    if listing.listing_status == "withdrawn":
        return False
    if criteria.city and normalize_text(listing.city) != normalize_text(criteria.city):
        return False
    if criteria.property_type and normalize_text(listing.property_type) != criteria.property_type:
        return False
    if criteria.min_rent is not None and listing.monthly_rent < criteria.min_rent:
        return False
    if criteria.max_rent is not None and listing.monthly_rent > criteria.max_rent:
        return False
    if (
        criteria.bedrooms is not None
        and listing.bedrooms is not None
        and listing.bedrooms < criteria.bedrooms
    ):
        return False
    if criteria.water_available and listing.water_available is False:
        return False
    if criteria.electricity_available and listing.electricity_available is False:
        return False
    if criteria.furnished is not None and listing.furnished not in (None, criteria.furnished):
        return False
    return True


@dataclass
class SearchOutcome:
    results: list[PropertySearchResult]
    total: int
    data_source: DataSourceName
    notices: list[str] = field(default_factory=list)


class SearchService:
    def __init__(
        self,
        primary_source: ListingSource,
        ranking_service: RankingService,
        risk_service: RiskService,
        fallback_source: ListingSource | None = None,
    ) -> None:
        self.primary_source = primary_source
        self.fallback_source = fallback_source
        self.ranking_service = ranking_service
        self.risk_service = risk_service

    def search(self, criteria: SearchCriteria, limit: int = 20) -> SearchOutcome:
        candidates, source_name, notices = self._load_candidates(criteria)
        matching = [item for item in candidates if satisfies_mandatory_criteria(item, criteria)]
        ranked = self.ranking_service.rank(matching, criteria)
        risk_signals = self.risk_service.assess(matching)

        results = [
            PropertySearchResult(
                property=item.property,
                rank=position,
                match_points=item.match_points,
                reasons=item.reasons,
                tradeoffs=item.tradeoffs,
                to_verify=item.to_verify,
                missing_information=missing_information(item.property),
                risk_signals=risk_signals[item.property.id],
            )
            for position, item in enumerate(ranked[:limit], start=1)
        ]
        logger.info(
            "Recherche via %s : %s candidat(s), %s retenu(s).",
            source_name, len(candidates), len(matching),
        )
        return SearchOutcome(
            results=results, total=len(matching), data_source=source_name, notices=notices
        )

    def get_property(self, property_id: int) -> PropertyRead | None:
        try:
            return self.primary_source.get_property(property_id)
        except KwatsurError:
            if self.fallback_source is None:
                raise
            return self.fallback_source.get_property(property_id)

    def _load_candidates(
        self, criteria: SearchCriteria
    ) -> tuple[list[PropertyRead], DataSourceName, list[str]]:
        try:
            return self.primary_source.find_candidates(criteria), self.primary_source.name, []
        except KwatsurError as error:
            if self.fallback_source is None:
                raise
            # Bascule transparente : la réponse indique clairement la source réellement utilisée.
            logger.warning("Source %s indisponible : %s", self.primary_source.name, error)
            notice = (
                f"Source « {self.primary_source.name} » indisponible ({error.public_message}) : "
                f"résultats lus dans « {self.fallback_source.name} »."
            )
            return (
                self.fallback_source.find_candidates(criteria),
                self.fallback_source.name,
                [notice],
            )
