"""Adaptateur Zetaris : exécute du SQL via l'API REST officielle et normalise les annonces.

Référence : https://api.saas.enterprise.zetaris.com/redoc/index.html (section « DB Query »).
  POST   /api/v1.0/query/sql/start          corps {"select", "pageLimit"}
  GET    /api/v1.0/query/sql/page           ?queryToken&pageLimit&pageNumber
  DELETE /api/v1.0/query/sql/close/{token}
Chaque appel exige « Authorization: Bearer <jeton API> », X-Request-ID (UUID) et X-Org-ID.
"""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.exceptions import (
    IntegrationNotConfiguredError,
    IntegrationUnavailableError,
    InvalidIntegrationResponseError,
)
from app.schemas.criteria import SearchCriteria
from app.schemas.property import DataSourceName, PropertyRead

logger = logging.getLogger(__name__)

PAGE_LIMIT = 100  # Maximum autorisé par l'API.
MAX_ROWS = 300

# Colonnes attendues dans la table enregistrée dans Zetaris (voir scripts/export_listings_csv.py).
LISTING_COLUMNS = (
    "id", "title", "description", "city", "neighborhood", "property_type",
    "monthly_rent", "currency", "bedrooms", "bathrooms", "furnished",
    "water_available", "electricity_available", "location_description",
    "latitude", "longitude", "source_name", "source_url", "contact_information",
    "listing_status", "verification_status", "source_is_demo", "last_seen_at",
)

TABLE_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){0,2}")
SAFE_TEXT_PATTERN = re.compile(r"[\w\s'’.,-]{1,120}")


class ZetarisClient:
    """Client HTTP minimal de l'API SQL de Zetaris."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        org_id: str,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.org_id = org_id.strip()
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.org_id.isdigit())

    def run_query(self, sql: str, max_rows: int = MAX_ROWS) -> list[dict[str, Any]]:
        """Exécute une requête, lit les pages nécessaires puis libère le curseur."""
        if not self.is_configured:
            raise IntegrationNotConfiguredError(
                "Zetaris n'est pas configuré (ZETARIS_BASE_URL, ZETARIS_API_KEY, ZETARIS_ORG_ID)."
            )
        with httpx.Client(
            base_url=self.base_url, timeout=self.timeout_seconds, transport=self.transport
        ) as http:
            first_page = self._request(
                http, "POST", "/api/v1.0/query/sql/start",
                json={"select": sql, "pageLimit": PAGE_LIMIT},
            )
            query_token = first_page.get("queryToken")
            try:
                rows = self._records(first_page)
                # La numérotation (0 ou 1) n'est pas précisée : on part de celle renvoyée.
                page_number = int(first_page.get("pageNumber", 0))
                last_page = page_number + int(first_page.get("totalPages", 1)) - 1
                while len(rows) < max_rows and page_number < last_page and query_token:
                    page_number += 1
                    page = self._request(
                        http, "GET", "/api/v1.0/query/sql/page",
                        params={
                            "queryToken": query_token,
                            "pageLimit": PAGE_LIMIT,
                            "pageNumber": page_number,
                        },
                    )
                    rows.extend(self._records(page))
            finally:
                if query_token:
                    self._close_quietly(http, query_token)
        return rows[:max_rows]

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Request-ID": str(uuid.uuid4()),
            "X-Org-ID": self.org_id,
        }

    def _request(self, http: httpx.Client, method: str, path: str, **kwargs: Any) -> dict:
        try:
            response = http.request(method, path, headers=self._headers(), **kwargs)
        except httpx.TimeoutException as error:
            raise IntegrationUnavailableError("Zetaris n'a pas répondu à temps.") from error
        except httpx.HTTPError as error:
            raise IntegrationUnavailableError("Zetaris est injoignable.") from error

        if response.status_code in (401, 403):
            raise IntegrationUnavailableError("Zetaris a refusé l'authentification.")
        if response.status_code >= 400:
            logger.warning("Zetaris %s %s a répondu %s", method, path, response.status_code)
            raise IntegrationUnavailableError("Zetaris a refusé la requête.")
        try:
            payload = response.json()
        except ValueError as error:
            raise InvalidIntegrationResponseError("Réponse Zetaris non JSON.") from error
        if not isinstance(payload, dict):
            raise InvalidIntegrationResponseError("Réponse Zetaris inattendue.")
        return payload

    @staticmethod
    def _records(page: dict) -> list[dict[str, Any]]:
        records = page.get("records") or []
        rows: list[dict[str, Any]] = []
        for record in records:
            # La spécification décrit des « records in JSON format » : objet ou chaîne JSON.
            if isinstance(record, str):
                try:
                    record = json.loads(record)
                except ValueError as error:
                    raise InvalidIntegrationResponseError("Ligne Zetaris illisible.") from error
            if not isinstance(record, dict):
                raise InvalidIntegrationResponseError("Ligne Zetaris sans noms de colonnes.")
            rows.append({str(key).lower(): value for key, value in record.items()})
        return rows

    def _close_quietly(self, http: httpx.Client, query_token: str) -> None:
        try:
            http.delete(f"/api/v1.0/query/sql/close/{query_token}", headers=self._headers())
        except httpx.HTTPError:
            logger.info("Fermeture du curseur Zetaris impossible ; il expirera côté serveur.")


def sql_text_literal(value: str) -> str:
    """Littéral SQL sûr : l'API n'accepte pas de paramètres liés, on valide puis échappe."""
    if not SAFE_TEXT_PATTERN.fullmatch(value):
        raise ValueError("Valeur refusée pour une requête Zetaris.")
    return "'" + value.replace("'", "''") + "'"


def build_candidates_query(table: str, criteria: SearchCriteria) -> str:
    """Seule la ville est filtrée côté Zetaris ; les autres filtres sont refaits en Python.

    Cela évite de dépendre du typage des colonnes importées (un CSV peut tout lire en texte).
    """
    sql = f"SELECT {', '.join(LISTING_COLUMNS)} FROM {table}"
    if criteria.city:
        sql += f" WHERE LOWER(city) = {sql_text_literal(criteria.city.lower())}"
    return sql


def _to_bool(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    text = str(value).strip().casefold()
    if text in ("true", "1", "oui", "yes", "t"):
        return True
    if text in ("false", "0", "non", "no", "f"):
        return False
    return None  # Vide ou inconnu : on ne devine pas.


def _to_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))


def _to_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_datetime(value: Any) -> datetime | None:
    text = _to_text(value)
    return datetime.fromisoformat(text) if text else None


def row_to_property(row: dict[str, Any]) -> PropertyRead:
    return PropertyRead(
        id=_to_int(row.get("id")),
        title=_to_text(row.get("title")),
        description=_to_text(row.get("description")),
        city=_to_text(row.get("city")),
        neighborhood=_to_text(row.get("neighborhood")),
        property_type=_to_text(row.get("property_type")),
        monthly_rent=_to_int(row.get("monthly_rent")),
        currency=_to_text(row.get("currency")) or "XAF",
        bedrooms=_to_int(row.get("bedrooms")),
        bathrooms=_to_int(row.get("bathrooms")),
        furnished=_to_bool(row.get("furnished")),
        water_available=_to_bool(row.get("water_available")),
        electricity_available=_to_bool(row.get("electricity_available")),
        location_description=_to_text(row.get("location_description")),
        latitude=_to_float(row.get("latitude")),
        longitude=_to_float(row.get("longitude")),
        source_name=_to_text(row.get("source_name")) or "Source non renseignée",
        source_url=_to_text(row.get("source_url")),
        contact_information=_to_text(row.get("contact_information")),
        listing_status=_to_text(row.get("listing_status")) or "unconfirmed",
        verification_status=_to_text(row.get("verification_status")) or "unverified",
        source_is_demo=bool(_to_bool(row.get("source_is_demo"))),
        last_seen_at=_to_datetime(row.get("last_seen_at")),
    )


class ZetarisListingSource:
    name: DataSourceName = "zetaris"

    def __init__(self, client: ZetarisClient, table: str) -> None:
        self.client = client
        self.table = table.strip()

    def find_candidates(self, criteria: SearchCriteria) -> list[PropertyRead]:
        self._ensure_table()
        rows = self.client.run_query(build_candidates_query(self.table, criteria))
        return self._normalize(rows)

    def get_property(self, property_id: int) -> PropertyRead | None:
        self._ensure_table()
        sql = (
            f"SELECT {', '.join(LISTING_COLUMNS)} FROM {self.table} "
            f"WHERE id = {int(property_id)}"
        )
        properties = self._normalize(self.client.run_query(sql, max_rows=1))
        return properties[0] if properties else None

    def _ensure_table(self) -> None:
        if not self.table:
            raise IntegrationNotConfiguredError("ZETARIS_LISTINGS_TABLE n'est pas renseigné.")
        # Le nom de table est injecté dans le SQL : on n'accepte que des identifiants simples.
        if not TABLE_NAME_PATTERN.fullmatch(self.table):
            raise IntegrationNotConfiguredError("ZETARIS_LISTINGS_TABLE est invalide.")

    @staticmethod
    def _normalize(rows: list[dict[str, Any]]) -> list[PropertyRead]:
        properties: list[PropertyRead] = []
        rejected = 0
        for row in rows:
            try:
                properties.append(row_to_property(row))
            except (ValidationError, ValueError, TypeError):
                rejected += 1
        if rejected:
            logger.warning("%s ligne(s) Zetaris ignorée(s) car incomplètes.", rejected)
        if rows and not properties:
            raise InvalidIntegrationResponseError(
                "Les lignes Zetaris ne correspondent pas au format des annonces."
            )
        return properties
