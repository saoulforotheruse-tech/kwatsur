"""Endpoints de recherche et de consultation des logements."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import PropertySearchDependency
from app.schemas.chat import SearchCriteria
from app.schemas.property import (
    PropertyRead,
    PropertySearch,
    PropertySearchResponse,
)

router = APIRouter(prefix="/api/properties", tags=["logements"])


@router.get("", response_model=PropertySearchResponse)
def search_properties(
    search_service: PropertySearchDependency,
    filters: Annotated[PropertySearch, Query()],
) -> PropertySearchResponse:
    criteria = SearchCriteria.model_validate(
        filters.model_dump(exclude={"limit"})
    )
    results, total = search_service.search(criteria, filters.limit)
    return PropertySearchResponse(total=total, results=results)


@router.get("/{property_id}", response_model=PropertyRead)
def get_property(
    property_id: int, search_service: PropertySearchDependency
) -> PropertyRead:
    property_read = search_service.get_property(property_id)
    if property_read is None:
        raise HTTPException(status_code=404, detail="Logement introuvable.")
    return property_read
