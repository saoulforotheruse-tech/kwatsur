"""Repository testé sur un vrai PostgreSQL (ignoré sans KWATSUR_TEST_DATABASE_URL).

Exemple : KWATSUR_TEST_DATABASE_URL=postgresql+psycopg://kwatsur:kwatsur_dev@localhost:5432/kwatsur_test
La base indiquée est vidée : n'utilisez jamais la base de l'application.
"""

import os
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.property import PropertySource
from app.repositories.property_repository import PropertyRepository
from app.schemas.criteria import SearchCriteria
from db.seed.seed_demo import demo_properties

TEST_DATABASE_URL = os.getenv("KWATSUR_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="KWATSUR_TEST_DATABASE_URL non défini"
)


@pytest.fixture
def postgres_session() -> Generator[Session, None, None]:
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        source = PropertySource(name="Démo", source_type="demo", is_demo=True)
        session.add(source)
        session.flush()
        session.add_all(demo_properties(source.id, datetime.now(timezone.utc)))
        session.commit()
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_prefilter_applies_mandatory_criteria_in_sql(postgres_session: Session) -> None:
    criteria = SearchCriteria(city="douala", max_rent=150000, bedrooms=2, water_available=True)

    candidates = PropertyRepository(postgres_session).find_candidates(criteria)

    assert candidates
    for listing in candidates:
        assert listing.city == "Douala"
        assert listing.monthly_rent <= 150000
        assert listing.bedrooms is None or listing.bedrooms >= 2
        assert listing.water_available is not False


def test_accented_city_matches(postgres_session: Session) -> None:
    candidates = PropertyRepository(postgres_session).find_candidates(SearchCriteria(city="yaounde"))

    assert candidates and all(listing.city == "Yaoundé" for listing in candidates)
