"""Fixtures partagées : base SQLite en mémoire, données fictives et client HTTP."""

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_llm_provider, get_settings
from app.core.config import Settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.property import PropertySource
from db.seed.seed_demo import DEMO_SOURCE_NAME, demo_properties
from tests.fakes import MockLLMProvider, scripted_extractions


def make_test_settings(**overrides: object) -> Settings:
    # _env_file=None : les tests ne lisent jamais le .env local ni de vraies clés.
    values = {"listing_source": "postgres", "llm_provider": "none", **overrides}
    return Settings(_env_file=None, **values)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database_session:
        source = PropertySource(name=DEMO_SOURCE_NAME, source_type="demo", is_demo=True)
        database_session.add(source)
        database_session.flush()
        database_session.add_all(demo_properties(source.id, datetime.now(timezone.utc)))
        database_session.commit()
        yield database_session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    """Mock par défaut : à remplacer dans chaque test via mock_llm.extraction_rule."""
    return MockLLMProvider(scripted_extractions())


@pytest.fixture
def client(session: Session, mock_llm: MockLLMProvider) -> Generator[TestClient, None, None]:
    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: make_test_settings()
    app.dependency_overrides[get_llm_provider] = lambda: mock_llm
    app.state.chat_rate_limiter = SlidingWindowRateLimiter(max_calls=100)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
