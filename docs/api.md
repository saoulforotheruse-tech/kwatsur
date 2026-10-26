# API Kwatsur

Documentation interactive générée par FastAPI : `/docs` (Swagger) et `/redoc`. Les erreurs ont toujours la forme `{"detail": "message lisible"}`, sans trace interne.

| Méthode | Route | Rôle |
| --- | --- | --- |
| GET | `/health` | État de l'API et de PostgreSQL (`503` si la base ne répond pas) |
| GET | `/api/integrations/status?live=false` | Configuration de Zetaris et du modèle ; `live=true` effectue un vrai appel |
| POST | `/api/chat` | Message à l'agent |
| GET | `/api/conversations/{conversation_id}` | Relire une conversation et ses critères |
| GET | `/api/properties` | Recherche par filtres (sans IA) |
| GET | `/api/properties/{id}` | Détail d'une annonce |
| POST | `/api/properties/{id}/contact-draft` | Brouillon de message (aucun envoi) |

## POST /api/chat

Requête :

```json
{ "message": "Un deux-chambres à Douala, 150 000 FCFA max", "conversation_id": null }
```

Réponse (extrait) :

```json
{
  "conversation_id": "1f0c…",
  "reply": "J'ai trouvé 5 logements…",
  "reply_generated_by": "nemotron",
  "criteria": { "city": "Douala", "max_rent": 150000, "bedrooms": 2, "preferences": [] },
  "needs_clarification": false,
  "searched": true,
  "total": 5,
  "data_source": "postgres",
  "notices": [],
  "results": [
    {
      "rank": 1,
      "match_points": 36,
      "property": { "id": 6, "title": "…", "monthly_rent": 95000, "source_is_demo": true },
      "reasons": ["Situé à Douala.", "2 chambre(s), comme demandé."],
      "tradeoffs": [],
      "to_verify": ["Accès à l'eau non précisé par l'annonce."],
      "missing_information": ["Logement meublé ou non"],
      "risk_signals": []
    }
  ],
  "scout": {
    "trace_id": "07d1…",
    "intent": "housing.search",
    "confidence": 1.0,
    "band": "high",
    "risk_level": "low",
    "risk_flags": [],
    "contract_id": "01M5WEJ1EA8D98130F5Q563PHS",
    "tool_plan": ["search_service.search", "llm.write_reply"],
    "model": "nvidia/nemotron-3-ultra-550b-a55b",
    "clarification_options": [],
    "latency_ms": 0.4
  }
}
```

`scout` résume la décision du moteur Meterless Scout Intent. `risk_level: "block"` (injection de prompt, demande de paiement) ou `clarification_options` non vide : aucun outil n'a été appelé.

Codes : `403` action refusée par le contrat d'exécution, `404` conversation inconnue, `422` message vide ou trop long, `429` trop de messages, `502` réponse IA inexploitable, `503` modèle non configuré ou indisponible, base indisponible.

## GET /api/properties

Paramètres facultatifs : `city`, `neighborhood` (préférence de classement), `property_type`, `min_rent`, `max_rent`, `bedrooms` (minimum), `water_available`, `electricity_available`, `furnished`, `limit` (1 à 100). Réponse : `total`, `data_source`, `notices`, `results` (même format que ci-dessus).

## Sémantique des critères

- **Obligatoires** (excluent) : ville, type, fourchette de loyer, chambres minimum, équipements exigés, mobilier demandé. Une valeur **inconnue** n'exclut pas l'annonce : elle apparaît dans `to_verify`.
- **Préférences** (classent) : quartier, mobilier, souhaits libres (`preferences`).
- `match_points` sert à ordonner les résultats d'une même recherche. Ce n'est ni une note ni une probabilité.
