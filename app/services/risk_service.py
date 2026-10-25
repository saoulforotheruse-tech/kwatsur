"""Données manquantes et signaux potentiels à vérifier.

Un signal n'est jamais une preuve d'arnaque : il invite l'utilisateur à vérifier un point
auprès de la source avant de s'engager.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from statistics import median

from app.schemas.property import PropertyRead

MIN_COMPARABLES = 4


def missing_information(listing: PropertyRead) -> list[str]:
    return [
        label
        for value, label in (
            (listing.neighborhood, "Quartier"),
            (listing.bedrooms, "Nombre de chambres"),
            (listing.bathrooms, "Nombre de salles de bain"),
            (listing.furnished, "Logement meublé ou non"),
            (listing.water_available, "Accès à l'eau"),
            (listing.electricity_available, "Accès à l'électricité"),
            (listing.last_seen_at, "Date de dernière observation"),
        )
        if value is None
    ]


class RiskService:
    def __init__(
        self,
        stale_after_days: int = 60,
        low_rent_ratio: float = 0.5,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.stale_after_days = stale_after_days
        self.low_rent_ratio = low_rent_ratio
        self.now = now

    def assess(self, listings: list[PropertyRead]) -> dict[int, list[str]]:
        """Signaux par identifiant d'annonce, comparés aux annonces du même lot."""
        return {listing.id: self._signals(listing, listings) for listing in listings}

    def _signals(self, listing: PropertyRead, batch: list[PropertyRead]) -> list[str]:
        signals: list[str] = []

        if listing.last_seen_at is None:
            signals.append("Date de dernière observation inconnue : disponibilité à confirmer.")
        else:
            seen_at = listing.last_seen_at
            if seen_at.tzinfo is None:
                seen_at = seen_at.replace(tzinfo=timezone.utc)
            age_in_days = (self.now() - seen_at).days
            if age_in_days > self.stale_after_days:
                signals.append(
                    f"Annonce observée il y a {age_in_days} jours : elle est peut-être déjà louée."
                )

        if not listing.source_is_demo and not listing.source_url:
            signals.append("Aucun lien vers l'annonce d'origine.")

        if len(missing_information(listing)) >= 4:
            signals.append("Annonce peu détaillée : plusieurs informations clés manquent.")

        comparables = [
            other.monthly_rent
            for other in batch
            if other.id != listing.id
            and other.city == listing.city
            and other.property_type == listing.property_type
            and other.bedrooms == listing.bedrooms
        ]
        if len(comparables) >= MIN_COMPARABLES:
            reference = median(comparables)
            if listing.monthly_rent < reference * self.low_rent_ratio:
                signals.append(
                    "Loyer nettement inférieur aux annonces comparables : signal potentiel, "
                    "à vérifier avant tout paiement."
                )

        return signals
