"""Affichage des montants : FCFA pour les annonces locales, code ISO sinon."""

from app.schemas.property import PropertyRead


def format_money(amount: int, currency: str = "XAF") -> str:
    label = "FCFA" if currency in ("XAF", "XOF") else currency
    return f"{amount:,}".replace(",", " ") + f" {label}"


def format_price(listing: PropertyRead) -> str:
    """« 150 000 FCFA par mois » pour une location, « 360 000 USD (prix de vente) » pour une vente."""
    amount = format_money(listing.monthly_rent, listing.currency)
    if listing.transaction_type == "rent":
        return f"{amount} par mois"
    if listing.transaction_type == "sale":
        return f"{amount} (prix de vente)"
    return f"{amount} (location ou vente non précisée)"


def price_in(listing: PropertyRead, currency: str) -> int | None:
    """Prix de l'annonce dans la monnaie du budget, ou None si on ne peut pas comparer sans conversion."""
    if listing.currency == currency:
        return listing.monthly_rent
    if currency == "USD" and listing.price_usd is not None:
        return listing.price_usd
    return None
