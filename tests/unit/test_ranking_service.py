"""Classement explicable et reproductible."""

from datetime import datetime, timedelta, timezone

from app.schemas.criteria import SearchCriteria
from app.services.ranking_service import RankingService, RankingWeights
from tests.factories import make_listing

CRITERIA = SearchCriteria(
    city="Douala", neighborhood="Bonamoussadi", max_rent=150000, bedrooms=2, water_available=True
)


def test_preferred_neighborhood_ranks_first_with_reason() -> None:
    elsewhere = make_listing(neighborhood="Makepe", monthly_rent=90000)
    preferred = make_listing(neighborhood="Bonamoussadi", monthly_rent=140000)

    ranked = RankingService().rank([elsewhere, preferred], CRITERIA)

    assert ranked[0].property.id == preferred.id
    assert "Dans le quartier souhaité (Bonamoussadi)." in ranked[0].reasons
    assert "Situé à Makepe, pas à Bonamoussadi." in ranked[1].tradeoffs


def test_unknown_amenity_is_flagged_not_counted() -> None:
    unknown_water = make_listing(water_available=None)
    confirmed_water = make_listing(water_available=True)

    ranked = RankingService().rank([unknown_water, confirmed_water], CRITERIA)

    assert ranked[0].property.id == confirmed_water.id
    unknown = ranked[1]
    assert "Accès à l'eau non précisé par l'annonce." in unknown.to_verify
    assert not any("eau" in reason for reason in unknown.reasons)


def test_exact_bedroom_count_beats_extra_bedrooms() -> None:
    three_bedrooms = make_listing(bedrooms=3)
    two_bedrooms = make_listing(bedrooms=2)

    ranked = RankingService().rank([three_bedrooms, two_bedrooms], CRITERIA)

    assert ranked[0].property.id == two_bedrooms.id


def test_ties_are_broken_by_rent_then_id() -> None:
    fixed_now = datetime(2026, 10, 25, tzinfo=timezone.utc)
    seen = fixed_now - timedelta(days=1)
    listings = [
        make_listing(id=30, monthly_rent=120000, last_seen_at=seen),
        make_listing(id=10, monthly_rent=120000, last_seen_at=seen),
        make_listing(id=20, monthly_rent=120000, last_seen_at=seen),
    ]
    service = RankingService(now=lambda: fixed_now)

    first = [item.property.id for item in service.rank(listings, CRITERIA)]
    second = [item.property.id for item in service.rank(list(reversed(listings)), CRITERIA)]

    assert first == second == [10, 20, 30]


def test_preference_mentioned_in_description_is_explained() -> None:
    criteria = SearchCriteria(city="Douala", preferences=["proche des transports"])
    mentioned = make_listing(description="À deux minutes des transports en commun.")
    silent = make_listing(description="Grand salon.")

    ranked = RankingService().rank([silent, mentioned], criteria)

    assert ranked[0].property.id == mentioned.id
    assert "« proche des transports » est mentionné dans l'annonce." in ranked[0].reasons
    assert "« proche des transports » : non mentionné dans l'annonce." in ranked[1].to_verify


def test_weights_are_configurable() -> None:
    cheap_elsewhere = make_listing(neighborhood="Makepe", monthly_rent=30000)
    expensive_preferred = make_listing(neighborhood="Bonamoussadi", monthly_rent=150000)
    budget_first = RankingService(RankingWeights(neighborhood_match=0, budget_headroom_max=50))

    ranked = budget_first.rank([expensive_preferred, cheap_elsewhere], CRITERIA)

    assert ranked[0].property.id == cheap_elsewhere.id
