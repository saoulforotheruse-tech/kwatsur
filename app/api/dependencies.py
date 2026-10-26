"""Dépendances partagées des routes FastAPI (assemblage des services)."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.db.session import get_session
from app.engines.scout import ModelProfile, ScoutEngine
from app.integrations.data.postgres import PostgresListingSource
from app.integrations.data.zetaris import ZetarisClient, ZetarisListingSource
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.factory import build_llm_provider
from app.integrations.llm.nemotron import NemotronProvider
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.property_repository import PropertyRepository
from app.services.agent_service import AgentService
from app.services.conversation_service import ConversationService
from app.services.integration_status_service import IntegrationStatusService
from app.services.ranking_service import RankingService
from app.services.risk_service import RiskService
from app.services.search_service import SearchService

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
    return ModelProfile("none", "template", False)


def get_scout_engine(app_settings: AppSettings) -> ScoutEngine:
    return ScoutEngine(build_model_profile(app_settings), app_settings.scout_signing_secret)


def get_agent_service(
    search_service: SearchServiceDependency,
    conversation_service: ConversationServiceDependency,
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    scout: Annotated[ScoutEngine, Depends(get_scout_engine)],
) -> AgentService:
    return AgentService(llm_provider, search_service, conversation_service, scout)


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
