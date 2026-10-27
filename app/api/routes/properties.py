"""Endpoints de recherche et de consultation des logements."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import ImageServiceDependency, SearchServiceDependency
from app.schemas.criteria import SearchCriteria
from app.schemas.property import (
    ContactDraftResponse,
    PropertyRead,
    PropertySearch,
    PropertySearchResponse,
)
from app.services.contact_service import build_contact_draft

router = APIRouter(prefix="/api/properties", tags=["logements"])


@router.get("", response_model=PropertySearchResponse, summary="Recherche par filtres")
def search_properties(
    search_service: SearchServiceDependency,
    image_service: ImageServiceDependency,
    filters: Annotated[PropertySearch, Query()],
) -> PropertySearchResponse:
    criteria = SearchCriteria.model_validate(filters.model_dump(exclude={"limit"}))
    outcome = search_service.search(criteria, filters.limit)
    return PropertySearchResponse(
        total=outcome.total,
        data_source=outcome.data_source,
        notices=outcome.notices,
        results=image_service.attach_photos(outcome.results),
    )


@router.get("/{property_id}", response_model=PropertyRead, summary="Détail d'un logement")
def get_property(property_id: int, search_service: SearchServiceDependency) -> PropertyRead:
    return _get_or_404(property_id, search_service)


@router.post(
    "/{property_id}/contact-draft",
    response_model=ContactDraftResponse,
    summary="Préparer un message de prise de contact (aucun envoi)",
)
def create_contact_draft(
    property_id: int, search_service: SearchServiceDependency
) -> ContactDraftResponse:
    return build_contact_draft(_get_or_404(property_id, search_service))


def _get_or_404(property_id: int, search_service: SearchServiceDependency) -> PropertyRead:
    property_read = search_service.get_property(property_id)
    if property_read is None:
        raise HTTPException(status_code=404, detail="Logement introuvable.")
    return property_read
