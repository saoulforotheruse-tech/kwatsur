"""Mode démo sans IA : extraction des critères par des règles déterministes."""

from app.integrations.llm.rules import parse_criteria
from app.schemas.criteria import SearchCriteria


def test_extracts_common_criteria_without_inventing() -> None:
    extraction = parse_criteria(
        "Je cherche un appartement de deux chambres à Douala vers Bonamoussadi, "
        "150 000 FCFA max, avec eau et électricité, proche des transports",
        SearchCriteria(),
    )

    updates = extraction.updates
    assert extraction.intent == "search"
    assert updates.city == "Douala"
    assert updates.neighborhood == "Bonamoussadi"
    assert updates.property_type == "appartement"
    assert updates.bedrooms == 2
    assert updates.max_rent == 150000
    assert updates.water_available is True and updates.electricity_available is True
    assert updates.furnished is None
    assert updates.preferences == ["proche des transports"]


def test_understands_short_amounts_minimum_and_furnishing() -> None:
    updates = parse_criteria("Studio meublé à Yaoundé, au moins 60k", SearchCriteria()).updates

    assert updates.city == "Yaoundé"
    assert updates.property_type == "studio"
    assert updates.min_rent == 60000 and updates.max_rent is None
    assert updates.furnished is True


def test_refinement_removes_neighborhood_and_keeps_unknowns_unknown() -> None:
    extraction = parse_criteria("Peu importe le quartier, mais 100 000 maximum", SearchCriteria(city="Douala"))

    assert extraction.intent == "refine"
    assert extraction.remove_fields == ["neighborhood"]
    assert extraction.updates.max_rent == 100000
    assert extraction.updates.city is None


def test_finds_a_known_neighborhood_written_in_lowercase() -> None:
    extraction = parse_criteria("je cherche un appart a bastos pas tres cher", SearchCriteria())

    assert extraction.updates.neighborhood == "Bastos"
    assert extraction.updates.city is None  # la ville est déduite ensuite par merge_criteria
