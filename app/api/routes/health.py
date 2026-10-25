"""Contrôle de disponibilité de l'application et de PostgreSQL."""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import DatabaseSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["santé"])


@router.get("/health")
def health_check(session: DatabaseSession) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        logger.error(
            "La vérification de la base de données a échoué (%s).",
            error.__class__.__name__,
        )
        raise HTTPException(
            status_code=503, detail="La base de données est indisponible."
        ) from error
    return {"status": "ok", "database": "ok"}
