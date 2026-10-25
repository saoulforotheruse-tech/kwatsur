"""Création de l'application FastAPI et assemblage de ses routes."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import health, properties
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router)
app.include_router(properties.router)


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(
    _request: Request, error: SQLAlchemyError
) -> JSONResponse:
    logger.error("Requête à la base de données échouée: %s", error.__class__.__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "La base de données est indisponible."},
    )


frontend_directory = Path(__file__).resolve().parents[1] / "frontend" / "public"
if frontend_directory.is_dir():
    app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
