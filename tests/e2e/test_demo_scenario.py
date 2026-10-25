"""Scénario de démonstration reproductible : demande → recherche → classement → affichage.

Le modèle est simulé (mock) pour que le test tourne sans réseau ; tout le reste est réel :
routes, services, filtres, classement, risques, persistance et frontend servi par l'API.
"""

from fastapi.testclient import TestClient

from tests.fakes import MockLLMProvider, scripted_extractions

DEMO_REQUEST = (
    "Je cherche un appartement de deux chambres à Douala, vers Bonamoussadi, avec un budget "
    "maximal de 150 000 FCFA par mois. Je veux de l'eau et de l'électricité, et je préfère "
    "être proche des transports."
)


def test_demo_scenario(client: TestClient, mock_llm: MockLLMProvider) -> None:
    mock_llm.extraction_rule = scripted_extractions(
        {
            "intent": "search",
            "updates": {
                "city": "Douala", "neighborhood": "Bonamoussadi", "property_type": "appartement",
                "bedrooms": 2, "max_rent": 150000, "water_available": True,
                "electricity_available": True, "preferences": ["proche des transports"],
            },
        },
        {"intent": "refine", "remove_fields": ["neighborhood"], "updates": {"max_rent": 100000}},
    )

    # 1. Le frontend est servi.
    assert "Kwatsur" in client.get("/").text

    # 2. Première demande en langage naturel.
    first = client.post("/api/chat", json={"message": DEMO_REQUEST}).json()
    results = first["results"]

    assert first["searched"] is True
    assert results, "Le jeu fictif contient des appartements correspondants."
    assert results[0]["property"]["neighborhood"] == "Bonamoussadi"
    for result in results:
        listing = result["property"]
        assert listing["city"] == "Douala"
        assert listing["property_type"] == "appartement"
        assert listing["monthly_rent"] <= 150000
        assert listing["bedrooms"] is None or listing["bedrooms"] >= 2
        assert listing["water_available"] is not False
        assert listing["source_is_demo"] is True
    # Les informations inconnues restent signalées, jamais inventées.
    assert any(result["to_verify"] for result in results)
    # L'annonce au loyer anormalement bas reçoit un signal potentiel.
    akwa = next(r for r in results if r["property"]["neighborhood"] == "Akwa")
    assert any("signal potentiel" in signal for signal in akwa["risk_signals"])

    # 3. L'utilisateur assouplit le quartier et baisse son budget : le contexte est conservé.
    second = client.post(
        "/api/chat",
        json={"message": "Peu importe le quartier, mais 100 000 maximum", "conversation_id": first["conversation_id"]},
    ).json()

    assert second["criteria"]["neighborhood"] is None
    assert second["criteria"]["bedrooms"] == 2
    assert second["criteria"]["water_available"] is True
    assert all(r["property"]["monthly_rent"] <= 100000 for r in second["results"])
