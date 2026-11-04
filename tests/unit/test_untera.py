"""Adaptateur Untera et routage par pays, testés avec des réponses HTTP simulées (MOCK, aucun appel réel)."""

import httpx
import pytest

from app.core.exceptions import IntegrationUnavailableError, InvalidIntegrationResponseError
from app.integrations.data.untera import (
    UnteraClient,
    UnteraListingSource,
    build_search_params,
    item_to_property,
)
from app.schemas.criteria import CriteriaExtraction, SearchCriteria
from app.services.criteria_service import merge_criteria
from app.services.money import format_price
from app.services.ranking_service import RankingService
from app.services.risk_service import RiskService
from app.services.search_service import RENT_FALLBACK_NOTICE, UNTERA_NOT_CONFIGURED, SearchService
from tests.factories import make_listing

ORIGIN = "https://api.untera.test"

# Forme observée sur untera.io (camelCase).
SITE_ITEM = {
    "id": "redfin_com_28347099", "sourceId": "redfin_az_us", "title": "13229 W Lisbon Ln",
    "price": 360000, "latitude": 33.61, "longitude": -112.34,
    "address": "13229 W Lisbon Ln, Surprise, AZ, 85379, US", "country": "US", "type": "residential",
    "features": "2 Baths,parking: 2 car garage", "images": '["/images/91/61/a-0.jpg"]', "sqm": 132.9,
    "status": "active", "sourceUrl": "https://www.redfin.com/AZ/Surprise/13229", "bedrooms": 4,
    "bathrooms": 2, "agencyName": "Redfin", "propertySubtype": "house", "transactionType": "sale",
    "normalizedPriceUsd": 360000, "originalPrice": None, "originalCurrency": None,
    "updatedAt": "2026-10-30T10:27:18.998Z",
}
# Forme des exemples de la documentation (snake_case).
DOC_ITEM = {
    "id": "idealista_123", "title": "Piso en Madrid", "price_usd": 1300, "original_price": 1200,
    "original_currency": "EUR", "url": "https://www.idealista.com/123", "images": ["/images/x.jpg"],
    "bedrooms": 2, "address": "Calle Mayor, Madrid", "country": "ES", "transaction_type": "rent",
}


def make_client(handler, api_key: str = "unt_test") -> UnteraClient:
    return UnteraClient(f"{ORIGIN}/api/v1", api_key, transport=httpx.MockTransport(handler))


def test_normalizes_site_item_as_sale_in_usd() -> None:
    listing = item_to_property(SITE_ITEM, ORIGIN)
    assert listing.id == "redfin_com_28347099"
    assert listing.transaction_type == "sale"
    assert (listing.monthly_rent, listing.currency, listing.price_usd) == (360000, "USD", 360000)
    assert listing.property_type == "maison"
    assert listing.photo_urls == [f"{ORIGIN}/images/91/61/a-0.jpg"]
    assert listing.source_name == "Redfin via Untera"
    # Inconnu chez la source : reste inconnu, jamais converti en False.
    assert listing.water_available is None and listing.furnished is None
    assert format_price(listing) == "360 000 USD (prix de vente)"


def test_normalizes_doc_item_keeps_original_currency() -> None:
    listing = item_to_property(DOC_ITEM, ORIGIN)
    assert (listing.monthly_rent, listing.currency, listing.price_usd) == (1200, "EUR", 1300)
    assert listing.transaction_type == "rent"
    assert format_price(listing) == "1 200 EUR par mois"


def test_unknown_transaction_stays_unknown() -> None:
    listing = item_to_property({**DOC_ITEM, "transaction_type": None}, ORIGIN)
    assert listing.transaction_type is None


def test_search_params_send_budget_only_in_usd() -> None:
    usd = SearchCriteria(country="US", city="Miami", max_rent=2000, currency="USD", transaction="rent", bedrooms=2)
    assert build_search_params(usd) == {
        "pageSize": 50, "country": "US", "location": "Miami", "transaction": "rent",
        "minBeds": 2, "maxPrice": 2000,
    }
    eur = SearchCriteria(country="PT", max_rent=1500, currency="EUR")
    assert "maxPrice" not in build_search_params(eur)


def test_search_sends_key_and_drops_land() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        land = {**SITE_ITEM, "id": "land_1", "propertySubtype": None, "type": "land"}
        return httpx.Response(200, json={"results": [SITE_ITEM, land]})

    listings = UnteraListingSource(make_client(handler)).find_candidates(SearchCriteria(country="US"))
    assert [item.id for item in listings] == ["redfin_com_28347099"]
    assert seen[0].headers["X-API-Key"] == "unt_test"
    assert seen[0].url.path == "/api/v1/listings/search"


def test_refused_key_is_reported() -> None:
    source = UnteraListingSource(make_client(lambda _r: httpx.Response(401, json={"error": "API key required."})))
    with pytest.raises(IntegrationUnavailableError):
        source.find_candidates(SearchCriteria(country="US"))


def test_unreadable_items_are_reported() -> None:
    source = UnteraListingSource(make_client(lambda _r: httpx.Response(200, json={"results": [{"title": "x"}]})))
    with pytest.raises(InvalidIntegrationResponseError):
        source.find_candidates(SearchCriteria(country="US"))


class FakeUnteraSource:
    """Source internationale simulée (MOCK) : renvoie des annonces selon la transaction demandée."""

    name = "untera"
    is_configured = True

    def __init__(self, rentals, sales) -> None:
        self.rentals, self.sales = rentals, sales
        self.queries: list[SearchCriteria] = []

    def find_candidates(self, criteria: SearchCriteria):
        self.queries.append(criteria)
        if criteria.transaction == "rent":
            return list(self.rentals)
        return list(self.rentals) + list(self.sales)


class LocalSource:
    name = "postgres"

    def __init__(self) -> None:
        self.called = False

    def find_candidates(self, _criteria):
        self.called = True
        return [make_listing(id=1, city="Douala")]


def make_service(remote, local=None) -> SearchService:
    return SearchService(local or LocalSource(), RankingService(), RiskService(), international_source=remote)


def sale(listing_id: str, price: int):
    return item_to_property({**SITE_ITEM, "id": listing_id, "price": price, "normalizedPriceUsd": price}, ORIGIN)


def test_cameroon_stays_local() -> None:
    remote, local = FakeUnteraSource([], []), LocalSource()
    outcome = make_service(remote, local).search(SearchCriteria(country="CM", city="Douala"))
    assert outcome.data_source == "postgres" and local.called and not remote.queries


def test_rent_request_falls_back_to_available_offers_clearly() -> None:
    remote = FakeUnteraSource([], [sale("a", 300000)])
    criteria = SearchCriteria(country="US", transaction="rent", max_rent=1500, currency="USD")
    outcome = make_service(remote).search(criteria)
    assert outcome.data_source == "untera"
    assert [result.property.id for result in outcome.results] == ["a"]
    assert RENT_FALLBACK_NOTICE in outcome.notices
    # Le budget mensuel n'est pas appliqué au prix de vente lors du repli.
    assert remote.queries[1].max_rent is None and remote.queries[1].transaction is None


def test_rentals_found_are_not_mixed_with_sales() -> None:
    rental = item_to_property({**DOC_ITEM, "country": "US", "price_usd": 1400, "original_price": None,
                               "original_currency": None}, ORIGIN)
    remote = FakeUnteraSource([rental], [sale("a", 300000)])
    outcome = make_service(remote).search(SearchCriteria(country="US", transaction="rent"))
    assert [result.property.id for result in outcome.results] == ["idealista_123"]
    assert RENT_FALLBACK_NOTICE not in outcome.notices


def test_budget_in_other_currency_is_not_converted() -> None:
    remote = FakeUnteraSource([], [sale("a", 300000)])
    criteria = SearchCriteria(country="US", transaction="sale", max_rent=100000, currency="EUR")
    outcome = make_service(remote).search(criteria)
    # Prix en USD, budget en EUR : non comparable, l'annonce reste et le point est à vérifier.
    assert outcome.total == 1
    assert any("aucune conversion" in item for item in outcome.results[0].to_verify)


def test_missing_key_is_said_without_local_fallback() -> None:
    local = LocalSource()
    service = SearchService(local, RankingService(), RiskService(), international_source=None)
    outcome = service.search(SearchCriteria(country="FR", city="Paris"))
    assert outcome.total == 0 and outcome.notices == [UNTERA_NOT_CONFIGURED] and not local.called


def test_changing_country_drops_old_city() -> None:
    current = SearchCriteria(country="CM", city="Douala", neighborhood="Akwa")
    criteria, _ = merge_criteria(current, CriteriaExtraction(updates={"country": "US"}))
    assert (criteria.country, criteria.city, criteria.neighborhood) == ("US", None, None)


def test_cameroon_city_sets_local_country() -> None:
    current = SearchCriteria(country="PT", city="Lisbon")
    criteria, _ = merge_criteria(current, CriteriaExtraction(updates={"city": "Douala"}))
    assert (criteria.country, criteria.city) == ("CM", "Douala")


# Extrait d'une vraie réponse de /listings/search (2026-11-02), réduit à deux annonces.
REAL_RESPONSE = {
    "page": 1, "page_size": 10, "count": 2,
    "results": [
        {"id": "remax_pt_123951021-28", "title": "Estação de Belmonte, Belmonte, Castelo Branco, 6250-011",
         "price_usd": 66847, "original_price": 59900, "original_currency": "EUR", "transaction": "sale",
         "type": "residential", "property_subtype": "house", "bedrooms": 5, "bathrooms": 3, "sqm": 718,
         "address": "Estação de Belmonte, Belmonte, Castelo Branco, 6250-011", "country": "PT",
         "latitude": 40.35, "longitude": -7.34,
         "images": [f"/images/18/16/1816b7c2a7f8b347-{n}.jpg" for n in range(6)],
         "source": "RE/MAX Portugal", "url": "https://untera.io/listings/remax_pt_123951021-28"},
        {"id": "remax_pt_123971046-22", "title": "Urbanização Quinta da Lomba, 27, Mealhada",
         "price_usd": 41849, "original_price": 37500, "original_currency": "EUR", "transaction": "sale",
         "type": "residential", "property_subtype": "land", "bedrooms": None, "bathrooms": None, "sqm": 397,
         "address": "Urbanização Quinta da Lomba, 27, Mealhada", "country": "PT",
         "images": ["/images/bb/9f/bb9f1b7061e84962-0.jpg"], "source": "RE/MAX Portugal",
         "url": "https://untera.io/listings/remax_pt_123971046-22"},
    ],
    "attribution": {"text": "Powered by Untera", "url": "https://untera.io"},
}


def test_real_response_is_normalized_and_land_dropped() -> None:
    source = UnteraListingSource(make_client(lambda _r: httpx.Response(200, json=REAL_RESPONSE)))
    [house] = source.find_candidates(SearchCriteria(country="PT"))
    assert house.id == "remax_pt_123951021-28"
    assert (house.monthly_rent, house.currency, house.price_usd) == (59900, "EUR", 66847)
    assert house.transaction_type == "sale" and house.property_type == "maison"
    assert house.source_name == "RE/MAX Portugal via Untera"
    assert house.description == "Surface indiquée par la source : 718 m²."
    assert house.photo_urls[0] == f"{ORIGIN}/images/18/16/1816b7c2a7f8b347-0.jpg"
    assert len(house.photo_urls) == 6


def test_source_photos_are_labelled_and_never_ai() -> None:
    from app.services.image_service import source_photo_reads

    house = item_to_property(REAL_RESPONSE["results"][0], ORIGIN)
    photos = source_photo_reads(house)
    assert len(photos) == 4
    assert all(photo.kind == "source_photo" and not photo.is_ai_generated for photo in photos)
    assert photos[0].url == house.photo_urls[0]
    assert photos[0].source_url == "https://untera.io/listings/remax_pt_123951021-28"


def test_unspecified_type_is_kept_for_apartment_search() -> None:
    # property_subtype null chez Untera : type inconnu, l'annonce reste et le point est « à vérifier ».
    unknown = item_to_property({**REAL_RESPONSE["results"][0], "property_subtype": None}, ORIGIN)
    remote = FakeUnteraSource([], [unknown])
    outcome = make_service(remote).search(SearchCriteria(country="PT", property_type="appartement"))
    assert outcome.total == 1
    assert any("Type de logement non précisé" in item for item in outcome.results[0].to_verify)


def test_address_outside_requested_city_is_flagged() -> None:
    house = item_to_property(REAL_RESPONSE["results"][0], ORIGIN)
    outcome = make_service(FakeUnteraSource([], [house])).search(SearchCriteria(country="PT", city="Lisbon"))
    assert any("ne mentionne pas Lisbon" in item for item in outcome.results[0].tradeoffs)


def test_rent_monthly_is_a_rental() -> None:
    listing = item_to_property({**DOC_ITEM, "transaction_type": None, "transaction": "rent_monthly"}, ORIGIN)
    assert listing.transaction_type == "rent"
