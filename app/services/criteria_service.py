"""Fusion des critères extraits par l'IA avec ceux déjà connus, validée par le backend."""

from typing import Any

from pydantic import ValidationError

from app.schemas.criteria import CriteriaExtraction, SearchCriteria, known_neighborhood

FIELD_LABELS = {
    "city": "ville",
    "neighborhood": "quartier",
    "property_type": "type de logement",
    "min_rent": "loyer minimum",
    "max_rent": "budget maximum",
    "bedrooms": "nombre de chambres",
    "water_available": "accès à l'eau",
    "electricity_available": "accès à l'électricité",
    "furnished": "meublé",
    "preferences": "préférences",
}


def _drop_blank_strings(updates: dict[str, Any]) -> dict[str, Any]:
    """Ignore les chaînes vides : le modèle les envoie souvent à la place de null."""
    return {
        field_name: value
        for field_name, value in updates.items()
        if not (isinstance(value, str) and not value.strip())
    }


def merge_criteria(
    current: SearchCriteria, extraction: CriteriaExtraction
) -> tuple[SearchCriteria, list[str]]:
    """Fusionne, puis déduit la ville d'un quartier connu (« Bastos » → Yaoundé)."""
    criteria, notices = _apply_updates(current, extraction)
    located, notice = locate_neighborhood(criteria)
    return located, notices + ([notice] if notice else [])


def locate_neighborhood(criteria: SearchCriteria) -> tuple[SearchCriteria, str | None]:
    """Corrige un quartier donné comme ville et complète la ville d'un quartier connu.

    Seuls les quartiers sans ambiguïté sont utilisés ; une ville déjà donnée n'est jamais remplacée
    par une autre ville.
    """
    if criteria.city is not None:
        found = known_neighborhood(criteria.city)
        if found is None:
            return criteria, None
        name, city = found
        updated = criteria.model_copy(update={"city": city, "neighborhood": criteria.neighborhood or name})
        return updated, f"{name} est un quartier de {city} : recherche à {city}."
    if criteria.neighborhood is not None:
        found = known_neighborhood(criteria.neighborhood)
        if found is not None:
            name, city = found
            return criteria.model_copy(update={"city": city}), f"{name} est un quartier de {city} : recherche à {city}."
    return criteria, None


def _apply_updates(
    current: SearchCriteria, extraction: CriteriaExtraction
) -> tuple[SearchCriteria, list[str]]:
    """Applique retraits puis mises à jour ; une valeur invalide est ignorée et signalée."""
    merged: dict[str, Any] = current.model_dump()
    for field_name in extraction.remove_fields:
        merged[field_name] = [] if field_name == "preferences" else None

    updates = _drop_blank_strings(extraction.updates.model_dump(exclude_none=True))
    # Les nouvelles préférences s'ajoutent aux anciennes au lieu de les remplacer.
    if "preferences" in updates:
        updates["preferences"] = merged["preferences"] + updates["preferences"]

    # Si l'utilisateur change une borne du budget, l'autre borne contradictoire est retirée.
    if "max_rent" in updates and "min_rent" not in updates:
        if merged["min_rent"] is not None and merged["min_rent"] > updates["max_rent"]:
            merged["min_rent"] = None
    if "min_rent" in updates and "max_rent" not in updates:
        if merged["max_rent"] is not None and merged["max_rent"] < updates["min_rent"]:
            merged["max_rent"] = None

    try:
        return SearchCriteria.model_validate({**merged, **updates}), []
    except ValidationError:
        pass

    # Repli champ par champ pour conserver les mises à jour valides.
    rejected: list[str] = []
    for field_name, value in updates.items():
        candidate = {**merged, field_name: value}
        try:
            SearchCriteria.model_validate(candidate)
            merged = candidate
        except ValidationError:
            rejected.append(FIELD_LABELS.get(field_name, field_name))
    notices = (
        [f"Valeur non retenue car invalide : {', '.join(rejected)}."] if rejected else []
    )
    return SearchCriteria.model_validate(merged), notices


def relaxation_suggestions(criteria: SearchCriteria) -> list[str]:
    """Critères qu'il est raisonnable d'assouplir quand aucun logement ne correspond."""
    suggestions: list[str] = []
    if criteria.max_rent is not None:
        suggestions.append(f"augmenter le budget maximum (actuellement {criteria.max_rent} FCFA)")
    if criteria.bedrooms:
        suggestions.append(f"réduire le nombre de chambres (actuellement {criteria.bedrooms})")
    if criteria.property_type:
        suggestions.append(f"accepter un autre type que « {criteria.property_type} »")
    if criteria.furnished is not None:
        suggestions.append("ne plus exiger un logement meublé ou non meublé")
    if criteria.min_rent is not None:
        suggestions.append("retirer le loyer minimum")
    if criteria.city:
        suggestions.append(f"chercher dans une autre ville que {criteria.city}")
    return suggestions
