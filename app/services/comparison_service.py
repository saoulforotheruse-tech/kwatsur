"""Comparaison textuelle de logements déjà classés. Une valeur inconnue reste « non renseignée »."""

from app.schemas.property import PropertySearchResult
from app.services.money import format_money, format_price

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
            f"n°{result.rank} — {listing.title} : {format_price(listing)}, "
            f"quartier {listing.neighborhood or UNKNOWN}, chambres {bedrooms}, "
            f"eau {_yes_no(listing.water_available)}, électricité {_yes_no(listing.electricity_available)}, "
            f"meublé {_yes_no(listing.furnished)}."
        )
    currencies = {result.property.currency for result in results}
    kinds = {result.property.transaction_type for result in results}
    # Écart chiffré seulement entre prix comparables (même monnaie, tous loyers ou toutes ventes).
    if len(currencies) == 1 and len(kinds) == 1 and None not in kinds:
        rents = [result.property.monthly_rent for result in results]
        cheapest = min(results, key=lambda result: (result.property.monthly_rent, result.rank))
        label = "loyer" if kinds == {"rent"} else "prix"
        lines.append(
            f"Écart de {label} : {format_money(max(rents) - min(rents), currencies.pop())}. "
            f"Le moins cher est le n°{cheapest.rank}."
        )
    else:
        lines.append("Prix non comparables directement (monnaies ou types d'annonce différents).")
    to_verify = sorted({item for result in results for item in result.to_verify})
    if to_verify:
        lines.append("À vérifier : " + " ; ".join(to_verify[:3]))
    return "\n".join(lines)
