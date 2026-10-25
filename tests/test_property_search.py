from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.property import Property, PropertySource
from app.repositories.property_repository import PropertyRepository
from app.schemas.chat import SearchCriteria
from app.services.search_service import SearchService
from db.seed import seed_demo


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        source = PropertySource(name="Annonces fictives", source_type="demo", is_demo=True)
        database_session.add(source)
        database_session.flush()
        database_session.add_all(
            [
                Property(
                    source_id=source.id,
                    source_property_id="douala-bonamoussadi",
                    title="Appartement Bonamoussadi",
                    city="Douala",
                    neighborhood="Bonamoussadi",
                    property_type="appartement",
                    monthly_rent=120000,
                    bedrooms=2,
                    water_available=True,
                    electricity_available=True,
                    listing_status="unconfirmed",
                ),
                Property(
                    source_id=source.id,
                    source_property_id="douala-bonapriso",
                    title="Appartement Bonapriso",
                    city="Douala",
                    neighborhood="Bonapriso",
                    property_type="appartement",
                    monthly_rent=90000,
                    bedrooms=2,
                    water_available=None,
                    electricity_available=True,
                    listing_status="unconfirmed",
                ),
                Property(
                    source_id=source.id,
                    source_property_id="yaounde-melen",
                    title="Studio Melen",
                    city="Yaoundé",
                    neighborhood="Melen",
                    property_type="studio",
                    monthly_rent=80000,
                    bedrooms=1,
                    listing_status="unconfirmed",
                ),
            ]
        )
        database_session.commit()
        yield database_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_search_filters_and_ranks_neighborhood_preference(session: Session) -> None:
    service = SearchService(PropertyRepository(session))

    results, total = service.search(
        SearchCriteria(
            city="douala",
            neighborhood="Bonamoussadi",
            max_rent=130000,
            bedrooms=2,
            water_available=True,
        )
    )

    assert total == 1
    assert results[0].property.title == "Appartement Bonamoussadi"
    assert "Le quartier correspond à « Bonamoussadi »." in results[0].reasons


def test_neighborhood_preference_orders_results_before_rent(session: Session) -> None:
    service = SearchService(PropertyRepository(session))

    results, _ = service.search(
        SearchCriteria(city="Douala", neighborhood="Bonamoussadi"), limit=10
    )

    assert [result.property.neighborhood for result in results] == [
        "Bonamoussadi",
        "Bonapriso",
    ]


def test_unknown_amenity_is_not_returned_as_false(session: Session) -> None:
    service = SearchService(PropertyRepository(session))

    results, total = service.search(SearchCriteria(city="Douala", max_rent=100000))

    assert total == 1
    assert results[0].property.water_available is None
    assert "Disponibilité de l’eau" in results[0].missing_information


def test_demo_seed_is_repeatable(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(seed_demo, "SessionLocal", test_session_factory)
    try:
        assert seed_demo.seed_demo_properties() == 3
        assert seed_demo.seed_demo_properties() == 0
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_http_search_and_not_found(session: Session) -> None:
    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            home = client.get("/")
            assert home.status_code == 200
            assert "Kwatsur" in home.text

            response = client.get(
                "/api/properties",
                params={"city": "Douala", "max_rent": 130000, "bedrooms": 2},
            )
            assert response.status_code == 200
            assert response.json()["total"] == 2

            health = client.get("/health")
            assert health.status_code == 200
            assert health.json()["database"] == "ok"

            property_detail = client.get("/api/properties/1")
            assert property_detail.status_code == 200
            assert property_detail.json()["source_is_demo"] is True

            missing_property = client.get("/api/properties/999")
            assert missing_property.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_invalid_rent_range_returns_validation_error() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/properties", params={"min_rent": 200000, "max_rent": 100000}
        )

    assert response.status_code == 422


def test_database_failure_returns_generic_service_error() -> None:
    def unavailable_session() -> Generator[Session, None, None]:
        raise OperationalError("SELECT 1", {}, RuntimeError("connection details"))
        yield

    app.dependency_overrides[get_session] = unavailable_session
    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 503
    assert "connection details" not in response.text
