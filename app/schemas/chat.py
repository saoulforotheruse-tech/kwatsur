"""Contrats Pydantic des critères de conversation."""

from pydantic import BaseModel, Field, model_validator

from app.schemas.property import PropertySearchResult


class SearchCriteria(BaseModel):
    city: str | None = Field(default=None, min_length=1, max_length=80)
    neighborhood: str | None = Field(default=None, min_length=1, max_length=120)
    min_rent: int | None = Field(default=None, ge=0)
    max_rent: int | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    water_available: bool | None = None
    electricity_available: bool | None = None
    furnished: bool | None = None

    @model_validator(mode="after")
    def validate_rent_range(self) -> "SearchCriteria":
        if (
            self.min_rent is not None
            and self.max_rent is not None
            and self.min_rent > self.max_rent
        ):
            raise ValueError("Le loyer minimum ne peut pas dépasser le loyer maximum.")
        return self


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    results: list[PropertySearchResult] = Field(default_factory=list)
