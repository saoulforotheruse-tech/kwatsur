"""Comparaison textuelle de logements déjà classés. Une valeur inconnue reste « non renseignée »."""

from app.schemas.property import PropertySearchResult
from app.services.ranking_service import format_fcfa

UNKNOWN = "non renseigné"


def _yes_no(value: bool | None) -> str:
    if value is None:
        return UNKNOWN
    return "oui" if value else "non"


def build_comparison(results: list[PropertySearchResult]) -> str:
    lines = ["Comparaison des logements demandés :"]
    for result in results:
        listing = result.property
        bedrooms = listing.bedrooms if listing.bedrooms is not None else UNKNOWN
        lines.append(
            f"n°{result.rank} — {listing.title} : {format_fcfa(listing.monthly_rent)}/mois, "
            f"quartier {listing.neighborhood or UNKNOWN}, chambres {bedrooms}, "
            f"eau {_yes_no(listing.water_available)}, électricité {_yes_no(listing.electricity_available)}, "
            f"meublé {_yes_no(listing.furnished)}."
        )
    rents = [result.property.monthly_rent for result in results]
    cheapest = min(results, key=lambda result: (result.property.monthly_rent, result.rank))
    lines.append(
        f"Écart de loyer : {format_fcfa(max(rents) - min(rents))}. "
        f"Le moins cher est le n°{cheapest.rank}."
    )
    to_verify = sorted({item for result in results for item in result.to_verify})
    if to_verify:
        lines.append("À vérifier : " + " ; ".join(to_verify[:3]))
    return "\n".join(lines)
