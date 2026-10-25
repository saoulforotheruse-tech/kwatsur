"""Contrats d'entrée et de sortie pour la recherche de logements."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class PropertySearch(BaseModel):
    city: str | None = Field(default=None, min_length=1, max_length=80)
    neighborhood: str | None = Field(default=None, min_length=1, max_length=120)
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
    model_config = ConfigDict(from_attributes=True)

    id: int
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


class PropertySearchResult(BaseModel):
    property: PropertyRead
    reasons: list[str]
    missing_information: list[str]


class PropertySearchResponse(BaseModel):
    total: int
    results: list[PropertySearchResult]
