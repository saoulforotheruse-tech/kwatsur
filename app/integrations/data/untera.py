"""Adaptateur Untera : annonces immobilières internationales (https://untera.io/developers).

Contrat documenté :
  GET {base}/listings/search   en-tête X-API-Key ; paramètres country, location, minPrice,
      maxPrice (USD), minBeds, minBaths, minSqm, maxSqm, type, transaction, sort, page,
      pageSize (≤ 50) ; réponse {"results": [...]}.
  GET {base}/listings/{id}     détail d'une annonce.
La documentation ne détaille pas le schéma d'une annonce : les noms de champs sont lus sous
leurs deux formes observées (exemples de la doc en snake_case, site untera.io en camelCase).
Offre gratuite : 1 000 requêtes/jour, 15/min, mention « Powered by Untera » obligatoire.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from pydantic import ValidationError

from app.core.exceptions import (
    IntegrationNotConfiguredError,
    IntegrationUnavailableError,
    InvalidIntegrationResponseError,
)
from app.schemas.criteria import SearchCriteria
from app.schemas.property import UNSPECIFIED_PROPERTY_TYPE, DataSourceName, PropertyRead

logger = logging.getLogger(__name__)

SEARCH_PATH = "/listings/search"
PAGE_SIZE = 50
LISTING_ID_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,200}")

# Sous-types Untera → types de logement de Kwatsur ; inconnu : valeur de la source telle quelle.
PROPERTY_TYPES = {
    "apartment": "appartement", "flat": "appartement", "condo": "appartement",
    "house": "maison", "townhouse": "maison", "detached": "maison", "semi-detached": "maison",
    "studio": "studio", "villa": "villa", "duplex": "duplex", "room": "chambre",
    "residential": UNSPECIFIED_PROPERTY_TYPE, "land": "terrain",
}
# Types qui ne sont pas des logements : jamais proposés.
NOT_HOUSING = {"terrain"}
RENT_WORDS = {"rent", "rental", "lease", "let", "to_rent"}
SALE_WORDS = {"sale", "sell", "buy", "for_sale"}


def _first(item: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = item.get(name)
        if value is not None and value != "":
            return value
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return round(float(value))


def _float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _datetime(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _transaction(value: Any) -> str | None:
    word = (_text(value) or "").casefold()
    # Valeurs observées : « sale », « rent_monthly » (d'autres périodes possibles : rent_weekly…).
    if word in RENT_WORDS or word.startswith("rent_"):
        return "rent"
    if word in SALE_WORDS:
        return "sale"
    return None  # Non précisé par la source : on ne devine pas.


def _price(item: dict[str, Any]) -> tuple[int, str, int | None]:
    """(montant affiché, monnaie, montant en USD) ; prix d'origine en priorité."""
    usd = _int(_first(item, "price_usd", "priceUsd", "normalizedPriceUsd", "normalized_price_usd"))
    original = _int(_first(item, "original_price", "originalPrice"))
    currency = _text(_first(item, "original_currency", "originalCurrency"))
    if original is not None and currency:
        return original, currency.upper(), usd
    if usd is None:
        # « price » est exprimé en USD dans la documentation et sur le site.
        usd = _int(item.get("price"))
    if usd is None:
        raise ValueError("Annonce Untera sans prix.")
    return usd, "USD", usd


def _photos(value: Any, image_origin: str) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            value = [value]
    if not isinstance(value, list):
        return []
    urls: list[str] = []
    for entry in value:
        raw = entry.get("url") if isinstance(entry, dict) else entry
        text = _text(raw)
        if not text:
            continue
        url = urljoin(image_origin + "/", text)
        if url.startswith("https://"):
            urls.append(url)
    return urls[:10]


def item_to_property(item: dict[str, Any], image_origin: str) -> PropertyRead:
    listing_id = _text(item.get("id"))
    if not listing_id or not LISTING_ID_PATTERN.fullmatch(listing_id):
        raise ValueError("Identifiant Untera manquant ou invalide.")
    amount, currency, usd = _price(item)
    address = _text(_first(item, "address", "location"))
    country = (_text(item.get("country")) or "").upper() or None
    subtype = (_text(_first(item, "property_subtype", "propertySubtype", "type")) or "").casefold()
    agency = _text(_first(item, "source", "agency_name", "agencyName", "source_id", "sourceId"))
    surface = _float(item.get("sqm"))
    status = (_text(item.get("status")) or "").casefold()
    return PropertyRead(
        id=listing_id,
        title=_text(_first(item, "title", "title_en", "titleEn")) or "Annonce sans titre",
        description=_text(_first(item, "description", "features"))
        or (f"Surface indiquée par la source : {surface:g} m²." if surface else None),
        city=_text(item.get("city")) or address or country or "Localisation non renseignée",
        neighborhood=None,
        property_type=PROPERTY_TYPES.get(subtype, subtype or UNSPECIFIED_PROPERTY_TYPE),
        monthly_rent=amount,
        currency=currency,
        bedrooms=_int(item.get("bedrooms")),
        bathrooms=_int(item.get("bathrooms")),
        furnished=None,
        water_available=None,
        electricity_available=None,
        location_description=address,
        latitude=_float(_first(item, "latitude", "lat")),
        longitude=_float(_first(item, "longitude", "lng", "lon")),
        source_name=f"{agency} via Untera" if agency else "Untera",
        source_url=_text(_first(item, "url", "source_url", "sourceUrl")),
        contact_information=None,
        listing_status="active" if status == "active" else "unconfirmed",
        verification_status="unverified",
        source_is_demo=False,
        last_seen_at=_datetime(_first(item, "updated_at", "updatedAt", "scraped_at", "scrapedAt")),
        transaction_type=_transaction(_first(item, "transaction_type", "transactionType", "transaction")),
        country=country,
        price_usd=usd,
        photo_urls=_photos(item.get("images"), image_origin),
    )


def build_search_params(criteria: SearchCriteria) -> dict[str, str | int]:
    """Pré-filtrage côté Untera ; le backend refait tous les filtres obligatoires ensuite."""
    params: dict[str, str | int] = {"pageSize": PAGE_SIZE}
    if criteria.country:
        params["country"] = criteria.country
    if criteria.city:
        params["location"] = criteria.city
    if criteria.transaction:
        params["transaction"] = criteria.transaction
    if criteria.bedrooms:
        params["minBeds"] = criteria.bedrooms
    # Untera filtre en USD : un budget dans une autre monnaie est appliqué par le backend.
    if criteria.budget_currency == "USD":
        if criteria.min_rent is not None:
            params["minPrice"] = criteria.min_rent
        if criteria.max_rent is not None:
            params["maxPrice"] = criteria.max_rent
    return params


class UnteraClient:
    """Client HTTP minimal de l'API Untera."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        parts = urlsplit(self.base_url)
        # Les chemins d'images (« /images/… ») sont servis par l'hôte de l'API.
        self.image_origin = f"{parts.scheme}://{parts.netloc}"

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def get(self, path: str, params: dict[str, str | int] | None = None) -> dict[str, Any] | None:
        """Corps JSON de la réponse, ou None si la ressource n'existe pas (404)."""
        if not self.is_configured:
            raise IntegrationNotConfiguredError("Untera n'est pas configuré (UNTERA_API_KEY).")
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as http:
                response = http.get(
                    self.base_url + path, params=params, headers={"X-API-Key": self.api_key}
                )
        except httpx.TimeoutException as error:
            raise IntegrationUnavailableError("Untera n'a pas répondu à temps.") from error
        except httpx.HTTPError as error:
            raise IntegrationUnavailableError("Untera est injoignable.") from error

        if response.status_code == 404:
            return None
        if response.status_code in (401, 403):
            raise IntegrationUnavailableError("Untera a refusé la clé API (UNTERA_API_KEY).")
        if response.status_code == 429:
            raise IntegrationUnavailableError("Quota Untera atteint : réessayez dans une minute.")
        if response.status_code >= 400:
            logger.warning("Untera GET %s a répondu %s", path, response.status_code)
            raise IntegrationUnavailableError("Untera a refusé la requête.")
        try:
            payload = response.json()
        except ValueError as error:
            raise InvalidIntegrationResponseError("Réponse Untera non JSON.") from error
        if not isinstance(payload, dict):
            raise InvalidIntegrationResponseError("Réponse Untera inattendue.")
        return payload


class UnteraListingSource:
    name: DataSourceName = "untera"

    def __init__(self, client: UnteraClient) -> None:
        self.client = client

    @property
    def is_configured(self) -> bool:
        return self.client.is_configured

    def find_candidates(self, criteria: SearchCriteria) -> list[PropertyRead]:
        payload = self.client.get(SEARCH_PATH, build_search_params(criteria)) or {}
        items = _first(payload, "results", "listings", "data")
        if items is None:
            items = []
        if not isinstance(items, list):
            raise InvalidIntegrationResponseError("Réponse Untera sans liste d'annonces.")
        return [item for item in self._normalize(items) if item.property_type not in NOT_HOUSING]

    def get_property(self, property_id: int | str) -> PropertyRead | None:
        listing_id = str(property_id)
        if not LISTING_ID_PATTERN.fullmatch(listing_id):
            return None
        payload = self.client.get(f"/listings/{listing_id}")
        if payload is None:
            return None
        item = _first(payload, "listing", "result", "data")
        properties = self._normalize([item if isinstance(item, dict) else payload])
        return properties[0] if properties else None

    def _normalize(self, items: list[Any]) -> list[PropertyRead]:
        properties: list[PropertyRead] = []
        rejected = 0
        for item in items:
            try:
                if not isinstance(item, dict):
                    raise TypeError("Annonce Untera illisible.")
                properties.append(item_to_property(item, self.client.image_origin))
            except (ValidationError, ValueError, TypeError):
                rejected += 1
        if rejected:
            logger.warning("%s annonce(s) Untera ignorée(s) car incomplètes.", rejected)
        if items and not properties:
            raise InvalidIntegrationResponseError(
                "Les annonces Untera ne correspondent pas au format attendu."
            )
        return properties
