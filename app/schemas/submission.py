"""Contrats des annonces proposées par les propriétaires dans le chat."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.criteria import canonical_city
from app.schemas.image import ImageRead

SubmissionStatus = Literal["draft", "pending", "approved", "rejected", "cancelled"]

# Ordre dans lequel l'agent pose ses questions : d'abord ce qui est indispensable à une annonce.
REQUIRED_FIELDS = ("city", "neighborhood", "property_type", "monthly_rent", "bedrooms", "contact_information")
OPTIONAL_FIELDS = ("water_available", "electricity_available", "furnished", "bathrooms", "description")

FIELD_QUESTIONS = {
    "city": "Dans quelle ville se trouve le logement (Douala, Yaoundé…) ?",
    "neighborhood": "Dans quel quartier se trouve-t-il ?",
    "property_type": "De quel type de logement s'agit-il (studio, chambre, appartement, maison…) ?",
    "monthly_rent": "Quel est le loyer mensuel, en FCFA ?",
    "bedrooms": "Combien de chambres compte-t-il (0 pour un studio) ?",
    "contact_information": (
        "Comment les locataires intéressés peuvent-ils vous joindre (téléphone ou e-mail) ? "
        "Ces coordonnées ne seront visibles qu'après validation par un administrateur."
    ),
}
FIELD_LABELS = {
    "city": "Ville",
    "neighborhood": "Quartier",
    "property_type": "Type",
    "monthly_rent": "Loyer mensuel",
    "bedrooms": "Chambres",
    "bathrooms": "Salles de bain",
    "furnished": "Meublé",
    "water_available": "Eau",
    "electricity_available": "Électricité",
    "contact_information": "Contact",
    "description": "Description",
}


class ListingFields(BaseModel):
    """Champs d'une annonce, tous facultatifs tant que la description n'est pas terminée."""

    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    city: str | None = Field(default=None, max_length=80)
    neighborhood: str | None = Field(default=None, max_length=120)
    property_type: str | None = Field(default=None, max_length=40)
    monthly_rent: int | None = Field(default=None, ge=0, le=100_000_000)
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    bathrooms: int | None = Field(default=None, ge=0, le=20)
    furnished: bool | None = None
    water_available: bool | None = None
    electricity_available: bool | None = None
    location_description: str | None = Field(default=None, max_length=500)
    contact_information: str | None = Field(default=None, max_length=200)

    @field_validator("city", mode="before")
    @classmethod
    def normalize_city(cls, value: object) -> object:
        if isinstance(value, str):
            return canonical_city(value) if value.strip() else None
        return value

    @field_validator(
        "title", "description", "neighborhood", "property_type", "location_description",
        "contact_information", mode="before",
    )
    @classmethod
    def blank_is_unknown(cls, value: object) -> object:
        # Une chaîne vide renvoyée par le modèle signifie « inconnu », jamais une valeur.
        if isinstance(value, str):
            return value.strip() or None
        return value


class ListingExtraction(BaseModel):
    """Ce que le modèle (ou les règles du mode démo) comprend d'un message du propriétaire."""

    updates: ListingFields = Field(default_factory=ListingFields)
    confirms: bool = False
    cancels: bool = False


class SubmissionRead(BaseModel):
    id: int
    status: SubmissionStatus
    fields: ListingFields
    missing_fields: list[str]
    images: list[ImageRead] = Field(default_factory=list)
    review_note: str | None = None
    created_at: datetime
    submitted_at: datetime | None = None


class SubmissionReview(BaseModel):
    note: str | None = Field(default=None, max_length=500)
