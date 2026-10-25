"""Classement explicable des résultats.

Chaque annonce reçoit des points d'adéquation, calculés uniquement à partir de données
connues. Les points servent à ordonner les résultats d'une même recherche : ce n'est ni
une note de qualité ni une probabilité.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.schemas.criteria import SearchCriteria, normalize_text
from app.schemas.property import PropertyRead

# Mots trop vagues pour prouver qu'une préférence est mentionnée dans une annonce.
GENERIC_WORDS = {
    "avec", "pour", "dans", "proche", "pres", "bien", "bonne", "bon", "tres",
    "plus", "sans", "avoir", "etre", "quartier", "logement", "maison", "zone",
}


@dataclass(frozen=True)
class RankingWeights:
    """Poids configurables de chaque facteur (Strategy : remplaçable sans toucher au code)."""

    neighborhood_match: int = 30
    exact_bedrooms: int = 15
    extra_bedrooms: int = 5
    confirmed_amenity: int = 10
    furnished_match: int = 5
    budget_headroom_max: int = 10
    preference_mentioned: int = 5
    recent_listing: int = 3
    known_detail: int = 1
    recent_days: int = 30


@dataclass
class RankedProperty:
    property: PropertyRead
    match_points: int = 0
    reasons: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    to_verify: list[str] = field(default_factory=list)


def format_fcfa(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " FCFA"


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", normalize_text(text))
    return [word for word in words if len(word) >= 4 and word not in GENERIC_WORDS]


def is_mentioned(preference: str, property_record: PropertyRead) -> bool:
    """Vrai si un mot significatif de la préférence apparaît dans le texte de l'annonce."""
    listing_text = " ".join(
        filter(None, (property_record.description, property_record.location_description))
    )
    # Comparaison sur les 6 premières lettres pour tolérer pluriels et accords.
    listing_stems = {word[:6] for word in _keywords(listing_text)}
    return any(word[:6] in listing_stems for word in _keywords(preference))


class RankingService:
    def __init__(
        self,
        weights: RankingWeights | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.weights = weights or RankingWeights()
        self.now = now

    def rank(
        self, properties: list[PropertyRead], criteria: SearchCriteria
    ) -> list[RankedProperty]:
        ranked = [self.evaluate(item, criteria) for item in properties]
        # Départage reproductible : points, puis loyer le plus bas, puis identifiant.
        ranked.sort(key=lambda item: (-item.match_points, item.property.monthly_rent, item.property.id))
        return ranked

    def evaluate(self, property_record: PropertyRead, criteria: SearchCriteria) -> RankedProperty:
        result = RankedProperty(property=property_record)
        self._explain_mandatory_criteria(result, criteria)
        self._score_neighborhood(result, criteria)
        self._score_bedrooms(result, criteria)
        self._score_amenities(result, criteria)
        self._score_budget(result, criteria)
        self._score_preferences(result, criteria)
        self._score_freshness_and_detail(result)
        return result

    def _explain_mandatory_criteria(self, result: RankedProperty, criteria: SearchCriteria) -> None:
        listing = result.property
        if criteria.city:
            result.reasons.append(f"Situé à {listing.city}.")
        if criteria.property_type:
            result.reasons.append(f"Type de logement : {listing.property_type}.")
        if criteria.max_rent is not None:
            result.reasons.append(
                f"Loyer de {format_fcfa(listing.monthly_rent)}, dans votre budget "
                f"(maximum {format_fcfa(criteria.max_rent)})."
            )

    def _score_neighborhood(self, result: RankedProperty, criteria: SearchCriteria) -> None:
        if not criteria.neighborhood:
            return
        listing = result.property
        if not listing.neighborhood:
            result.to_verify.append("Quartier non renseigné par l'annonce.")
        elif normalize_text(criteria.neighborhood) in normalize_text(listing.neighborhood):
            result.match_points += self.weights.neighborhood_match
            result.reasons.append(f"Dans le quartier souhaité ({listing.neighborhood}).")
        else:
            result.tradeoffs.append(
                f"Situé à {listing.neighborhood}, pas à {criteria.neighborhood}."
            )

    def _score_bedrooms(self, result: RankedProperty, criteria: SearchCriteria) -> None:
        bedrooms = result.property.bedrooms
        if criteria.bedrooms is None:
            return
        if bedrooms is None:
            result.to_verify.append("Nombre de chambres non renseigné par l'annonce.")
        elif bedrooms == criteria.bedrooms:
            result.match_points += self.weights.exact_bedrooms
            result.reasons.append(f"{bedrooms} chambre(s), comme demandé.")
        else:
            result.match_points += self.weights.extra_bedrooms
            result.reasons.append(
                f"{bedrooms} chambres (vous en demandiez au moins {criteria.bedrooms})."
            )

    def _score_amenities(self, result: RankedProperty, criteria: SearchCriteria) -> None:
        listing = result.property
        for required, value, label in (
            (criteria.water_available, listing.water_available, "eau"),
            (criteria.electricity_available, listing.electricity_available, "électricité"),
        ):
            if not required:
                continue
            if value is True:
                result.match_points += self.weights.confirmed_amenity
                result.reasons.append(f"Accès à l'{label} indiqué par l'annonce.")
            else:
                result.to_verify.append(f"Accès à l'{label} non précisé par l'annonce.")

        if criteria.furnished is not None:
            wanted = "meublé" if criteria.furnished else "non meublé"
            if listing.furnished is None:
                result.to_verify.append(f"L'annonce ne précise pas si le logement est {wanted}.")
            elif listing.furnished == criteria.furnished:
                result.match_points += self.weights.furnished_match
                result.reasons.append(f"Logement {wanted}, comme souhaité.")

    def _score_budget(self, result: RankedProperty, criteria: SearchCriteria) -> None:
        if not criteria.max_rent:
            return
        headroom = (criteria.max_rent - result.property.monthly_rent) / criteria.max_rent
        result.match_points += round(self.weights.budget_headroom_max * max(headroom, 0))
        if headroom >= 0.10:
            result.reasons.append(f"Loyer {round(headroom * 100)} % sous votre budget maximum.")

    def _score_preferences(self, result: RankedProperty, criteria: SearchCriteria) -> None:
        for preference in criteria.preferences:
            if is_mentioned(preference, result.property):
                result.match_points += self.weights.preference_mentioned
                result.reasons.append(f"« {preference} » est mentionné dans l'annonce.")
            else:
                result.to_verify.append(f"« {preference} » : non mentionné dans l'annonce.")

    def _score_freshness_and_detail(self, result: RankedProperty) -> None:
        listing = result.property
        if listing.last_seen_at is not None:
            seen_at = listing.last_seen_at
            if seen_at.tzinfo is None:
                seen_at = seen_at.replace(tzinfo=timezone.utc)
            if (self.now() - seen_at).days <= self.weights.recent_days:
                result.match_points += self.weights.recent_listing
                result.reasons.append("Annonce observée récemment par la source.")

        known_details = sum(
            value is not None
            for value in (
                listing.bedrooms,
                listing.bathrooms,
                listing.furnished,
                listing.water_available,
                listing.electricity_available,
            )
        )
        result.match_points += known_details * self.weights.known_detail
