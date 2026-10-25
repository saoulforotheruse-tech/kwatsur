"""Contrôle de disponibilité de l'application, de PostgreSQL et des intégrations."""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import AppSettings, DatabaseSession, IntegrationStatusDependency
from app.services.integration_status_service import IntegrationStatus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["santé"])


@router.get("/health", summary="État de l'API et de la base")
def health_check(session: DatabaseSession, app_settings: AppSettings) -> dict[str, str]:
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
    return {
        "status": "ok",
        "database": "ok",
        "listing_source": app_settings.listing_source,
        "llm_provider": app_settings.llm_provider,
    }


@router.get(
    "/api/integrations/status",
    response_model=list[IntegrationStatus],
    summary="Configuration des intégrations ; live=true effectue un vrai appel",
)
def integrations_status(
    status_service: IntegrationStatusDependency, live: bool = False
) -> list[IntegrationStatus]:
    return status_service.report(live)
