"""Dépendances partagées des routes FastAPI."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.repositories.property_repository import PropertyRepository
from app.services.search_service import SearchService

DatabaseSession = Annotated[Session, Depends(get_session)]


def get_property_search_service(session: DatabaseSession) -> SearchService:
    return SearchService(PropertyRepository(session))


PropertySearchDependency = Annotated[
    SearchService, Depends(get_property_search_service)
]
