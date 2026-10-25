"""Adaptateur Zetaris testé avec des réponses HTTP simulées (aucun appel réel)."""

import json

import httpx
import pytest

from app.core.exceptions import (
    IntegrationNotConfiguredError,
    IntegrationUnavailableError,
    InvalidIntegrationResponseError,
)
from app.integrations.data.zetaris import (
    ZetarisClient,
    ZetarisListingSource,
    build_candidates_query,
    sql_text_literal,
)
from app.schemas.criteria import SearchCriteria

ROW = {
    "ID": "7", "TITLE": "Appartement Zetaris", "CITY": "Douala", "NEIGHBORHOOD": "Bonamoussadi",
    "PROPERTY_TYPE": "appartement", "MONTHLY_RENT": "120000", "CURRENCY": "XAF",
    "BEDROOMS": "2", "BATHROOMS": "", "FURNISHED": "false", "WATER_AVAILABLE": "true",
    "ELECTRICITY_AVAILABLE": "", "SOURCE_NAME": "Données fictives Kwatsur",
    "SOURCE_IS_DEMO": "true", "LISTING_STATUS": "unconfirmed",
    "VERIFICATION_STATUS": "unverified", "LAST_SEEN_AT": "2026-10-20T10:00:00+00:00",
}


def make_client(handler) -> ZetarisClient:
    return ZetarisClient(
        base_url="https://zetaris.test",
        api_key="test-token",
        org_id="42",
        transport=httpx.MockTransport(handler),
    )


def test_runs_query_pages_results_and_closes_cursor() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["X-Org-ID"] == "42"
        assert request.headers["X-Request-ID"]
        if request.url.path == "/api/v1.0/query/sql/start":
            assert json.loads(request.content) == {"select": "SELECT 1", "pageLimit": 100}
            return httpx.Response(200, json={
                "records": [{"id": 1}], "pageNumber": 1, "pageLimit": 100,
                "totalCount": 2, "totalPages": 2, "queryToken": "tok",
            })
        if request.url.path == "/api/v1.0/query/sql/page":
            assert request.url.params["queryToken"] == "tok"
            assert request.url.params["pageNumber"] == "2"
            return httpx.Response(200, json={
                "records": [json.dumps({"id": 2})], "pageNumber": 2,
                "totalCount": 2, "totalPages": 2, "queryToken": "tok",
            })
        return httpx.Response(200, json={"msg": "closed"})

    rows = make_client(handler).run_query("SELECT 1")

    assert rows == [{"id": 1}, {"id": 2}]
    assert calls[-1] == ("DELETE", "/api/v1.0/query/sql/close/tok")


def test_rows_are_normalized_without_inventing_values() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={
                "records": [ROW], "pageNumber": 0, "pageLimit": 100,
                "totalCount": 1, "totalPages": 1, "queryToken": "tok",
            })
        return httpx.Response(200, json={})

    source = ZetarisListingSource(make_client(handler), "kwatsur.listings")
    listing = source.find_candidates(SearchCriteria(city="Douala"))[0]

    assert listing.id == 7 and listing.monthly_rent == 120000
    assert listing.water_available is True
    assert listing.furnished is False
    assert listing.electricity_available is None
    assert listing.bathrooms is None
    assert listing.source_is_demo is True


def test_query_only_pushes_down_escaped_city() -> None:
    sql = build_candidates_query("kwatsur.listings", SearchCriteria(city="Douala", max_rent=100000))

    assert sql.endswith("FROM kwatsur.listings WHERE LOWER(city) = 'douala'")
    assert sql_text_literal("Ngoa-Ekellé l'est") == "'Ngoa-Ekellé l''est'"


def test_dangerous_text_is_refused() -> None:
    with pytest.raises(ValueError):
        sql_text_literal("x'; DROP TABLE listings; --")


def test_invalid_table_name_is_refused_before_any_call() -> None:
    source = ZetarisListingSource(make_client(lambda _r: httpx.Response(500)), "listings; DROP")

    with pytest.raises(IntegrationNotConfiguredError):
        source.find_candidates(SearchCriteria(city="Douala"))


def test_authentication_error_is_reported() -> None:
    with pytest.raises(IntegrationUnavailableError, match="authentification"):
        make_client(lambda _r: httpx.Response(401)).run_query("SELECT 1")


def test_missing_configuration_is_explicit() -> None:
    client = ZetarisClient(base_url="", api_key="", org_id="")

    with pytest.raises(IntegrationNotConfiguredError):
        client.run_query("SELECT 1")


def test_rows_without_expected_columns_are_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "records": [{"foo": "bar"}], "pageNumber": 0, "totalPages": 1, "queryToken": "tok",
        })

    with pytest.raises(InvalidIntegrationResponseError):
        ZetarisListingSource(make_client(handler), "listings").find_candidates(SearchCriteria())
