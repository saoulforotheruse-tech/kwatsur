"""Critères de recherche structurés et sortie attendue du modèle IA."""

import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Ramène les variantes courantes vers les types utilisés dans les annonces.
PROPERTY_TYPE_SYNONYMS = {
    "appart": "appartement",
    "apartment": "appartement",
    "flat": "appartement",
    "studio moderne": "studio",
    "chambre moderne": "chambre",
    "room": "chambre",
    "house": "maison",
}

CriteriaField = Literal[
    "city",
    "neighborhood",
    "property_type",
    "min_rent",
    "max_rent",
    "bedrooms",
    "water_available",
    "electricity_available",
    "furnished",
    "preferences",
]


def normalize_text(value: str) -> str:
    """Minuscules sans accents, pour comparer « Yaoundé » et « yaounde »."""
    decomposed = unicodedata.normalize("NFKD", value.strip().casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


# Orthographe de référence des villes, telle qu'enregistrée dans les annonces.
CANONICAL_CITIES = {
    normalize_text(name): name
    for name in (
        "Douala", "Yaoundé", "Bafoussam", "Bamenda", "Garoua", "Maroua",
        "Ngaoundéré", "Bertoua", "Ebolowa", "Kribi", "Limbe", "Buea",
    )
}


def canonical_city(name: str) -> str:
    return CANONICAL_CITIES.get(normalize_text(name), name.strip())


class SearchCriteria(BaseModel):
    """Critères conservés pendant une conversation.

    Obligatoires (filtrent) : ville, type, budget, chambres minimum, équipements exigés.
    Préférences (classent) : quartier, mobilier, souhaits libres.
    Un équipement à True est exigé ; None signifie « sans exigence ».
    """

    city: str | None = Field(default=None, min_length=1, max_length=80)
    neighborhood: str | None = Field(default=None, min_length=1, max_length=120)
    property_type: str | None = Field(default=None, min_length=1, max_length=40)
    min_rent: int | None = Field(default=None, ge=0)
    max_rent: int | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    water_available: bool | None = None
    electricity_available: bool | None = None
    furnished: bool | None = None
    preferences: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("city", mode="before")
    @classmethod
    def normalize_city(cls, value: object) -> object:
        if isinstance(value, str):
            return canonical_city(value) if value.strip() else None
        return value

    @field_validator("neighborhood", mode="before")
    @classmethod
    def strip_neighborhood(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("property_type", mode="before")
    @classmethod
    def normalize_property_type(cls, value: object) -> object:
        if not isinstance(value, str) or not value.strip():
            return None
        lowered = value.strip().casefold()
        return PROPERTY_TYPE_SYNONYMS.get(lowered, lowered)

    @field_validator("preferences", mode="before")
    @classmethod
    def clean_preferences(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip()[:80]
            if text and text.casefold() not in (seen.casefold() for seen in cleaned):
                cleaned.append(text)
        return cleaned[:8]

    @model_validator(mode="after")
    def validate_rent_range(self) -> "SearchCriteria":
        if (
            self.min_rent is not None
            and self.max_rent is not None
            and self.min_rent > self.max_rent
        ):
            raise ValueError("Le loyer minimum ne peut pas dépasser le loyer maximum.")
        return self

    def is_empty(self) -> bool:
        return self == SearchCriteria()


class CriteriaUpdates(BaseModel):
    """Valeurs nouvellement mentionnées par l'utilisateur, toutes facultatives."""

    city: str | None = None
    neighborhood: str | None = None
    property_type: str | None = None
    min_rent: int | None = None
    max_rent: int | None = None
    bedrooms: int | None = None
    water_available: bool | None = None
    electricity_available: bool | None = None
    furnished: bool | None = None
    preferences: list[str] | None = None


class CriteriaExtraction(BaseModel):
    """Format JSON que le modèle doit produire à chaque message utilisateur."""

    intent: Literal["search", "refine", "question", "other"] = "search"
    updates: CriteriaUpdates = Field(default_factory=CriteriaUpdates)
    remove_fields: list[CriteriaField] = Field(default_factory=list)
    clarification_question: str | None = Field(default=None, max_length=300)
