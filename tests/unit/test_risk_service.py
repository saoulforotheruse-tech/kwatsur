"""Données manquantes et signaux potentiels."""

from datetime import datetime, timedelta, timezone

from app.services.risk_service import RiskService, missing_information
from tests.factories import make_listing

NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)


def test_unknown_values_are_listed_as_missing() -> None:
    listing = make_listing(water_available=None, bathrooms=None)

    assert missing_information(listing) == ["Nombre de salles de bain", "Accès à l'eau"]


def test_rent_far_below_comparables_is_a_potential_signal() -> None:
    comparables = [make_listing(monthly_rent=rent) for rent in (100000, 110000, 120000, 130000)]
    suspicious = make_listing(monthly_rent=40000)

    signals = RiskService(now=lambda: NOW).assess([*comparables, suspicious])

    assert any("signal potentiel" in signal for signal in signals[suspicious.id])
    assert all("Loyer" not in " ".join(signals[item.id]) for item in comparables)


def test_old_or_undated_listing_needs_availability_check() -> None:
    old = make_listing(last_seen_at=NOW - timedelta(days=90))
    undated = make_listing(last_seen_at=None)

    signals = RiskService(now=lambda: NOW).assess([old, undated])

    assert "90 jours" in signals[old.id][0]
    assert "disponibilité à confirmer" in signals[undated.id][0]


def test_real_listing_without_link_is_flagged() -> None:
    listing = make_listing(source_is_demo=False, source_url=None, last_seen_at=NOW)

    signals = RiskService(now=lambda: NOW).assess([listing])

    assert "Aucun lien vers l'annonce d'origine." in signals[listing.id]


def test_signals_never_claim_fraud() -> None:
    batch = [make_listing(monthly_rent=rent, last_seen_at=None) for rent in (100000,) * 4]
    batch.append(make_listing(monthly_rent=10000, last_seen_at=None, water_available=None,
                              bathrooms=None, furnished=None))

    all_signals = " ".join(" ".join(items) for items in RiskService(now=lambda: NOW).assess(batch).values())

    assert "arnaque" not in all_signals.lower()
