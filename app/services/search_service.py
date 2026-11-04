"""Recherche déterministe : source d'annonces → filtres obligatoires → classement → risques.

Routage par pays : les pays couverts par la source locale (Zetaris/PostgreSQL, Cameroun par
défaut) gardent le parcours historique ; tout autre pays interroge Untera.
"""

import logging
from dataclasses import dataclass, field

from app.core.exceptions import KwatsurError
from app.integrations.data.base import ListingSource
from app.integrations.data.untera import UnteraListingSource
from app.schemas.criteria import LOCAL_DEFAULT_COUNTRY, SearchCriteria, normalize_text
from app.schemas.property import (
    UNSPECIFIED_PROPERTY_TYPE,
    DataSourceName,
    PropertyId,
    PropertyRead,
    PropertySearchResult,
)
from app.services.money import price_in
from app.services.ranking_service import RankingService
from app.services.risk_service import RiskService, missing_information

logger = logging.getLogger(__name__)

UNTERA_ATTRIBUTION = "Annonces internationales : Powered by Untera (https://untera.io)."
UNTERA_NOT_CONFIGURED = (
    "La recherche hors Cameroun passe par Untera, qui n'est pas configuré sur ce serveur "
    "(UNTERA_API_KEY manquante)."
)
RENT_FALLBACK_NOTICE = (
    "Aucune location trouvée sur Untera pour cette recherche. Voici les annonces disponibles : "
    "chaque carte indique s'il s'agit d'une vente (prix de vente, pas un loyer). "
    "Votre budget n'a pas été appliqué à ces prix."
)


def satisfies_mandatory_criteria(
    listing: PropertyRead, criteria: SearchCriteria, international: bool = False
) -> bool:
    """Filtre appliqué en Python à toutes les sources, quel que soit leur pré-filtrage.

    Une donnée inconnue ne fait pas échouer un critère : seule une valeur contraire exclut.
    `international` : annonce Untera, dont la ville est déjà filtrée par la source (l'annonce ne
    porte qu'une adresse) et qui peut être une vente.
    """
    if listing.listing_status == "withdrawn":
        return False
    if (
        not international
        and criteria.city
        and normalize_text(listing.city) != normalize_text(criteria.city)
    ):
        return False
    if (
        criteria.property_type
        and listing.property_type != UNSPECIFIED_PROPERTY_TYPE
        and normalize_text(listing.property_type) != criteria.property_type
    ):
        return False
    if (
        international
        and criteria.transaction
        and listing.transaction_type not in (None, criteria.transaction)
    ):
        return False
    # Monnaies différentes sans conversion fournie : prix non comparable, l'annonce reste à vérifier.
    price = price_in(listing, criteria.budget_currency)
    if price is not None and criteria.min_rent is not None and price < criteria.min_rent:
        return False
    if price is not None and criteria.max_rent is not None and price > criteria.max_rent:
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
        international_source: UnteraListingSource | None = None,
        local_countries: frozenset[str] = frozenset({LOCAL_DEFAULT_COUNTRY}),
    ) -> None:
        self.primary_source = primary_source
        self.fallback_source = fallback_source
        self.international_source = international_source
        self.local_countries = local_countries
        self.ranking_service = ranking_service
        self.risk_service = risk_service

    def is_international(self, criteria: SearchCriteria) -> bool:
        """Vrai si le pays demandé n'est pas couvert par la source locale (pays inconnu : local)."""
        return criteria.country is not None and criteria.country not in self.local_countries

    def search(self, criteria: SearchCriteria, limit: int = 20) -> SearchOutcome:
        if self.is_international(criteria):
            return self._search_international(criteria, limit)
        candidates, source_name, notices = self._load_candidates(criteria)
        matching = [item for item in candidates if satisfies_mandatory_criteria(item, criteria)]
        return self._outcome(len(candidates), matching, criteria, source_name, notices, limit)

    def get_property(self, property_id: PropertyId) -> PropertyRead | None:
        if isinstance(property_id, str):
            # Identifiant texte : annonce internationale (les annonces locales ont un entier).
            source = self.international_source
            return source.get_property(property_id) if source and source.is_configured else None
        try:
            return self.primary_source.get_property(property_id)
        except KwatsurError:
            if self.fallback_source is None:
                raise
            return self.fallback_source.get_property(property_id)

    def _search_international(self, criteria: SearchCriteria, limit: int) -> SearchOutcome:
        source = self.international_source
        if source is None or not source.is_configured:
            return SearchOutcome(results=[], total=0, data_source="untera", notices=[UNTERA_NOT_CONFIGURED])
        notices = [UNTERA_ATTRIBUTION]
        try:
            candidates = source.find_candidates(criteria)
            matching = [item for item in candidates if satisfies_mandatory_criteria(item, criteria, True)]
            if not matching and criteria.transaction == "rent":
                # Untera publie surtout des ventes : on montre ce qui existe, sans le faire passer
                # pour une location, et sans appliquer un budget mensuel à un prix de vente.
                criteria = criteria.model_copy(
                    update={"transaction": None, "min_rent": None, "max_rent": None}
                )
                candidates = source.find_candidates(criteria)
                matching = [
                    item for item in candidates if satisfies_mandatory_criteria(item, criteria, True)
                ]
                if matching:
                    notices.append(RENT_FALLBACK_NOTICE)
        except KwatsurError as error:
            # Pas de repli local : la base locale ne couvre pas ce pays.
            logger.warning("Untera indisponible : %s", error)
            return SearchOutcome(
                results=[], total=0, data_source="untera",
                notices=[f"Annonces internationales indisponibles : {error.public_message}"],
            )
        return self._outcome(len(candidates), matching, criteria, "untera", notices, limit)

    def _outcome(
        self,
        candidate_count: int,
        matching: list[PropertyRead],
        criteria: SearchCriteria,
        source_name: DataSourceName,
        notices: list[str],
        limit: int,
    ) -> SearchOutcome:
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
            source_name, candidate_count, len(matching),
        )
        return SearchOutcome(
            results=results, total=len(matching), data_source=source_name, notices=notices
        )

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
