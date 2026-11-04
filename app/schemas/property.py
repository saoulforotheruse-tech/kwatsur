"""Contrats d'entrée et de sortie pour la recherche de logements."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.schemas.image import ImageRead

DataSourceName = Literal["postgres", "zetaris", "untera"]
# Type de logement que la source ne précise pas : ne fait jamais échouer le critère « type ».
UNSPECIFIED_PROPERTY_TYPE = "type non précisé"
# Identifiant : entier pour les annonces locales, texte pour une source externe (Untera).
PropertyId = int | str


class PropertySearch(BaseModel):
    """Filtres de la recherche manuelle (paramètres de requête GET)."""

    city: str | None = Field(default=None, min_length=1, max_length=80)
    neighborhood: str | None = Field(default=None, min_length=1, max_length=120)
    property_type: str | None = Field(default=None, min_length=1, max_length=40)
    min_rent: int | None = Field(default=None, ge=0)
    max_rent: int | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    water_available: bool | None = None
    electricity_available: bool | None = None
    furnished: bool | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_rent_range(self) -> "PropertySearch":
        if (
            self.min_rent is not None
            and self.max_rent is not None
            and self.min_rent > self.max_rent
        ):
            raise ValueError("Le loyer minimum ne peut pas dépasser le loyer maximum.")
        return self


class PropertyRead(BaseModel):
    """Annonce normalisée, quelle que soit la source (PostgreSQL, Zetaris ou Untera).

    `monthly_rent` porte le prix affiché : loyer mensuel si `transaction_type` vaut « rent »,
    prix de vente s'il vaut « sale » (annonces internationales d'Untera).
    """

    model_config = ConfigDict(from_attributes=True)

    id: PropertyId
    title: str
    description: str | None
    city: str
    neighborhood: str | None
    property_type: str
    monthly_rent: int
    currency: str
    bedrooms: int | None
    bathrooms: int | None
    furnished: bool | None
    water_available: bool | None
    electricity_available: bool | None
    location_description: str | None
    latitude: float | None
    longitude: float | None
    source_name: str
    source_url: HttpUrl | None
    contact_information: str | None
    listing_status: str
    verification_status: str
    source_is_demo: bool
    last_seen_at: datetime | None
    # None : la source ne précise pas s'il s'agit d'une location ou d'une vente.
    transaction_type: Literal["rent", "sale"] | None = "rent"
    country: str | None = None
    # Prix converti en USD par la source, quand elle le fournit (comparaison de budgets en USD).
    price_usd: int | None = None
    # Photos publiées par l'annonce d'origine (URL absolues de la source), jamais générées.
    photo_urls: list[str] = Field(default_factory=list)


class PropertySearchResult(BaseModel):
    """Annonce classée avec l'explication déterministe de son rang."""

    property: PropertyRead
    rank: int
    match_points: int = Field(
        description="Points d'adéquation relatifs à cette recherche, pas une probabilité."
    )
    reasons: list[str]
    tradeoffs: list[str]
    to_verify: list[str]
    missing_information: list[str]
    risk_signals: list[str]
    # Photos du propriétaire puis illustrations IA (chacune étiquetée), si le logement en a.
    images: list[ImageRead] = Field(default_factory=list)


class PropertySearchResponse(BaseModel):
    total: int
    data_source: DataSourceName
    notices: list[str] = Field(default_factory=list)
    results: list[PropertySearchResult]


class ContactDraftResponse(BaseModel):
    """Brouillon de message : Kwatsur n'envoie rien lui-même."""

    property_id: PropertyId
    message: str
    contact_information: str | None
    source_url: HttpUrl | None
    notice: str
