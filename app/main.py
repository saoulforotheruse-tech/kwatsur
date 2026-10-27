"""Création de l'application FastAPI et assemblage de ses routes."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import chat, health, properties
from app.core.config import settings
from app.core.exceptions import KwatsurError
from app.core.logging import configure_logging
from app.core.rate_limit import SlidingWindowRateLimiter
from app.engines.scout.registry import load_registry
from app.engines.scout.sense import self_test as scout_self_test

configure_logging()
logger = logging.getLogger(__name__)

# Scout Intent : le Stage 1 doit tenir sous 16 ms, sinon l'application refuse de démarrer.
logger.info("scout.selftest stage1Ms=%.3f", scout_self_test(load_registry()))

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="Agent conversationnel de recherche de logements au Cameroun.",
)
app.state.chat_rate_limiter = SlidingWindowRateLimiter(settings.chat_rate_limit_per_minute)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(properties.router)


@app.exception_handler(KwatsurError)
async def handle_application_error(_request: Request, error: KwatsurError) -> JSONResponse:
    # Seul le message public est renvoyé : jamais de trace ni de détail de configuration.
    logger.warning("%s : %s", error.__class__.__name__, error.public_message)
    return JSONResponse(status_code=error.status_code, content={"detail": error.public_message})


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(
    _request: Request, error: SQLAlchemyError
) -> JSONResponse:
    logger.error("Requête à la base de données échouée: %s", error.__class__.__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "La base de données est indisponible."},
    )


# Interface autonome (hackathon) : http://127.0.0.1:8000/static/
static_directory = Path(__file__).resolve().parent / "static"
if static_directory.is_dir():
    app.mount("/static", StaticFiles(directory=static_directory, html=True), name="static")

# Hors Docker (développement, tests), l'API sert aussi l'interface. L'image Docker ne la contient
# pas : l'interface tourne dans son propre conteneur nginx (frontend/docker-compose.yml).
frontend_directory = Path(__file__).resolve().parents[1] / "frontend" / "public"
if frontend_directory.is_dir():
    app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
