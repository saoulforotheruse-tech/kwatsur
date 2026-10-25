"""Filtres obligatoires, absence de résultats et bascule de source."""

import pytest

from app.core.exceptions import IntegrationUnavailableError
from app.schemas.criteria import SearchCriteria
from app.schemas.property import DataSourceName, PropertyRead
from app.services.ranking_service import RankingService
from app.services.risk_service import RiskService
from app.services.search_service import SearchService, satisfies_mandatory_criteria
from tests.factories import make_listing


class InMemorySource:
    """Source d'annonces en mémoire (mock), conforme au contrat ListingSource."""

    def __init__(self, listings: list[PropertyRead], name: DataSourceName = "postgres") -> None:
        self.listings = listings
        self.name = name

    def find_candidates(self, criteria: SearchCriteria) -> list[PropertyRead]:
        return list(self.listings)

    def get_property(self, property_id: int) -> PropertyRead | None:
        return next((item for item in self.listings if item.id == property_id), None)


class FailingSource:
    name: DataSourceName = "zetaris"

    def find_candidates(self, criteria: SearchCriteria) -> list[PropertyRead]:
        raise IntegrationUnavailableError("Zetaris est injoignable.")

    def get_property(self, property_id: int) -> PropertyRead | None:
        raise IntegrationUnavailableError("Zetaris est injoignable.")


def make_service(primary, fallback=None) -> SearchService:
    return SearchService(primary, RankingService(), RiskService(), fallback_source=fallback)


@pytest.mark.parametrize(
    ("listing_overrides", "expected"),
    [
        ({}, True),
        ({"city": "Yaoundé"}, False),
        ({"monthly_rent": 160000}, False),
        ({"bedrooms": 1}, False),
        ({"bedrooms": None}, True),  # inconnu : conservé, signalé à vérifier
        ({"water_available": False}, False),
        ({"water_available": None}, True),
        ({"listing_status": "withdrawn"}, False),
    ],
)
def test_mandatory_filters(listing_overrides: dict, expected: bool) -> None:
    criteria = SearchCriteria(city="douala", max_rent=150000, bedrooms=2, water_available=True)

    assert satisfies_mandatory_criteria(make_listing(**listing_overrides), criteria) is expected


def test_results_respect_every_mandatory_criterion() -> None:
    listings = [make_listing(monthly_rent=rent) for rent in (90000, 150000, 200000)]

    outcome = make_service(InMemorySource(listings)).search(SearchCriteria(city="Douala", max_rent=150000))

    assert outcome.total == 2
    assert all(item.property.monthly_rent <= 150000 for item in outcome.results)
    assert [item.rank for item in outcome.results] == [1, 2]


def test_no_result_returns_empty_list_without_invention() -> None:
    outcome = make_service(InMemorySource([make_listing()])).search(SearchCriteria(city="Kribi"))

    assert outcome.total == 0
    assert outcome.results == []


def test_falls_back_to_postgres_and_says_so() -> None:
    service = make_service(FailingSource(), fallback=InMemorySource([make_listing()]))

    outcome = service.search(SearchCriteria(city="Douala"))

    assert outcome.data_source == "postgres"
    assert outcome.total == 1
    assert "zetaris" in outcome.notices[0]


def test_without_fallback_the_source_error_is_raised() -> None:
    with pytest.raises(IntegrationUnavailableError):
        make_service(FailingSource()).search(SearchCriteria(city="Douala"))
