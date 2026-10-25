"""Validation et fusion des critères de recherche."""

import pytest
from pydantic import ValidationError

from app.schemas.criteria import CriteriaExtraction, SearchCriteria
from app.services.criteria_service import merge_criteria, relaxation_suggestions


def extraction(updates: dict | None = None, remove: list[str] | None = None) -> CriteriaExtraction:
    return CriteriaExtraction.model_validate(
        {"intent": "refine", "updates": updates or {}, "remove_fields": remove or []}
    )


def test_rejects_inverted_rent_range() -> None:
    with pytest.raises(ValidationError):
        SearchCriteria(min_rent=200000, max_rent=100000)


def test_normalizes_city_type_and_preferences() -> None:
    criteria = SearchCriteria(
        city=" yaounde ",
        property_type="Apartment",
        preferences=["Calme", "calme", " proche des transports "],
    )

    assert criteria.city == "Yaoundé"
    assert criteria.property_type == "appartement"
    assert criteria.preferences == ["Calme", "proche des transports"]


def test_merge_keeps_previous_criteria_when_budget_changes() -> None:
    current = SearchCriteria(city="Douala", neighborhood="Bonamoussadi", bedrooms=2, max_rent=150000)

    merged, notices = merge_criteria(current, extraction({"max_rent": 120000}))

    assert merged.max_rent == 120000
    assert (merged.city, merged.neighborhood, merged.bedrooms) == ("Douala", "Bonamoussadi", 2)
    assert notices == []


def test_merge_removes_abandoned_fields_and_appends_preferences() -> None:
    current = SearchCriteria(city="Douala", neighborhood="Akwa", preferences=["calme"])

    merged, _ = merge_criteria(
        current, extraction({"preferences": ["parking"]}, remove=["neighborhood"])
    )

    assert merged.neighborhood is None
    assert merged.preferences == ["calme", "parking"]


def test_merge_drops_contradictory_min_rent() -> None:
    current = SearchCriteria(city="Douala", min_rent=100000)

    merged, _ = merge_criteria(current, extraction({"max_rent": 80000}))

    assert merged.max_rent == 80000
    assert merged.min_rent is None


def test_merge_ignores_invalid_value_and_reports_it() -> None:
    current = SearchCriteria(city="Douala")

    merged, notices = merge_criteria(current, extraction({"bedrooms": 99, "max_rent": 90000}))

    assert merged.bedrooms is None
    assert merged.max_rent == 90000
    assert notices and "nombre de chambres" in notices[0]


def test_relaxation_suggestions_cover_active_constraints() -> None:
    suggestions = relaxation_suggestions(SearchCriteria(city="Douala", max_rent=50000, bedrooms=3))

    assert any("budget" in item for item in suggestions)
    assert any("chambres" in item for item in suggestions)
