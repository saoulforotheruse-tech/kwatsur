"""Dépendances partagées des routes FastAPI (assemblage des services)."""

import hmac
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.db.session import get_session
from app.engines.scout import ModelProfile, ScoutEngine
from app.integrations.data.postgres import PostgresListingSource
from app.core.exceptions import KwatsurError
from app.integrations.data.zetaris import ZetarisClient, ZetarisListingSource
from app.integrations.image_description.base import ImageDescriber
from app.integrations.image_description.factory import build_image_describer
from app.integrations.image_generation.base import ImageGenerationProvider
from app.integrations.image_generation.factory import build_image_provider
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.factory import build_llm_provider
from app.integrations.llm.nemotron import NemotronProvider
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.image_repository import ImageRepository
from app.repositories.property_repository import PropertyRepository
from app.repositories.submission_repository import SubmissionRepository
from app.services.agent_service import AgentService
from app.services.conversation_service import ConversationService
from app.services.image_service import ImageService
from app.services.image_storage import LocalImageStore
from app.services.integration_status_service import IntegrationStatusService
from app.services.ranking_service import RankingService
from app.services.risk_service import RiskService
from app.services.search_service import SearchService
from app.services.submission_service import SubmissionService

DatabaseSession = Annotated[Session, Depends(get_session)]


def get_settings() -> Settings:
    return settings


AppSettings = Annotated[Settings, Depends(get_settings)]


def build_zetaris_client(app_settings: Settings) -> ZetarisClient:
    return ZetarisClient(
        base_url=app_settings.zetaris_base_url,
        api_key=app_settings.zetaris_api_key,
        org_id=app_settings.zetaris_org_id,
        timeout_seconds=app_settings.zetaris_timeout_seconds,
    )


def get_search_service(session: DatabaseSession, app_settings: AppSettings) -> SearchService:
    postgres_source = PostgresListingSource(PropertyRepository(session))
    ranking, risk = RankingService(), RiskService()
    if app_settings.listing_source == "zetaris":
        zetaris_source = ZetarisListingSource(
            build_zetaris_client(app_settings), app_settings.zetaris_listings_table
        )
        fallback = postgres_source if app_settings.zetaris_fallback_to_postgres else None
        return SearchService(zetaris_source, ranking, risk, fallback_source=fallback)
    return SearchService(postgres_source, ranking, risk)


SearchServiceDependency = Annotated[SearchService, Depends(get_search_service)]


def get_llm_provider(app_settings: AppSettings) -> LLMProvider:
    return build_llm_provider(app_settings)


def get_conversation_service(session: DatabaseSession) -> ConversationService:
    return ConversationService(ConversationRepository(session))


ConversationServiceDependency = Annotated[ConversationService, Depends(get_conversation_service)]


def build_model_profile(app_settings: Settings) -> ModelProfile:
    if app_settings.llm_provider == "meterless":
        return ModelProfile("meterless", app_settings.meterless_model, bool(app_settings.meterless_api_key))
    if app_settings.llm_provider == "nemotron":
        return ModelProfile("nvidia", app_settings.nemotron_model, bool(app_settings.nemotron_api_key))
    if app_settings.llm_provider == "rules":
        return ModelProfile("rules", "règles déterministes (mode démo)", False)
    return ModelProfile("none", "template", False)


def get_scout_engine(app_settings: AppSettings) -> ScoutEngine:
    return ScoutEngine(build_model_profile(app_settings), app_settings.scout_signing_secret)


def get_image_provider(app_settings: AppSettings) -> ImageGenerationProvider:
    return build_image_provider(app_settings)


def get_image_store(app_settings: AppSettings) -> LocalImageStore:
    return LocalImageStore(Path(app_settings.media_directory), app_settings.image_upload_max_bytes)


def get_image_describer(app_settings: AppSettings) -> ImageDescriber:
    return build_image_describer(app_settings)


def get_image_service(
    session: DatabaseSession,
    app_settings: AppSettings,
    provider: Annotated[ImageGenerationProvider, Depends(get_image_provider)],
    store: Annotated[LocalImageStore, Depends(get_image_store)],
    describer: Annotated[ImageDescriber, Depends(get_image_describer)],
) -> ImageService:
    return ImageService(
        provider,
        store,
        ImageRepository(session),
        app_settings.image_generation_daily_limit,
        describer=describer,
        max_reference_photos=app_settings.vision_max_reference_photos,
        max_reference_photo_bytes=app_settings.vision_max_photo_bytes,
    )


ImageServiceDependency = Annotated[ImageService, Depends(get_image_service)]


def get_submission_service(
    session: DatabaseSession, image_service: ImageServiceDependency
) -> SubmissionService:
    return SubmissionService(SubmissionRepository(session), ImageRepository(session), image_service)


SubmissionServiceDependency = Annotated[SubmissionService, Depends(get_submission_service)]


def get_agent_service(
    search_service: SearchServiceDependency,
    conversation_service: ConversationServiceDependency,
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    scout: Annotated[ScoutEngine, Depends(get_scout_engine)],
    submission_service: SubmissionServiceDependency,
    image_service: ImageServiceDependency,
    app_settings: AppSettings,
) -> AgentService:
    return AgentService(
        llm_provider, search_service, conversation_service, scout,
        submissions=submission_service, images=image_service,
        scout_routing=app_settings.scout_routing_enabled,
    )


AgentServiceDependency = Annotated[AgentService, Depends(get_agent_service)]


def get_integration_status_service(app_settings: AppSettings) -> IntegrationStatusService:
    provider = build_llm_provider(app_settings)
    chat_client = provider.chat_client if isinstance(provider, NemotronProvider) else None
    return IntegrationStatusService(app_settings, build_zetaris_client(app_settings), chat_client)


IntegrationStatusDependency = Annotated[
    IntegrationStatusService, Depends(get_integration_status_service)
]


def enforce_chat_rate_limit(request: Request) -> None:
    client_key = request.client.host if request.client else "inconnu"
    request.app.state.chat_rate_limiter.check(client_key)


class AdminNotConfiguredError(KwatsurError):
    status_code = 503
    public_message = "L'administration est fermée : renseignez ADMIN_TOKEN dans le fichier .env."


class AdminUnauthorizedError(KwatsurError):
    status_code = 401
    public_message = "Jeton d'administration invalide."


def require_admin(
    app_settings: AppSettings,
    admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> None:
    """Protège la validation des annonces par le jeton ADMIN_TOKEN (comparaison à temps constant)."""
    expected = app_settings.admin_token.strip()
    if not expected:
        raise AdminNotConfiguredError()
    if not admin_token or not hmac.compare_digest(admin_token.encode(), expected.encode()):
        raise AdminUnauthorizedError()
