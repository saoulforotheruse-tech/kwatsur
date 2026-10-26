# Kwatsur en 5 minutes

À lire en premier si tu rejoins le projet. Les détails sont dans `architecture.md`, `api.md` et `exigences.md`.

## Ce que fait Kwatsur

Tu écris « Un deux-chambres à Douala vers Bonamoussadi, 150 000 FCFA max, avec eau ». Kwatsur comprend la demande, cherche dans les annonces, garde celles qui respectent tes critères, les classe, puis t'explique pourquoi chaque logement est proposé et ce qu'il faut vérifier. Il n'invente jamais une information absente.

## Le principe à retenir

> **L'IA comprend et explique. Le code décide.**

Nemotron transforme la phrase en critères, puis rédige l'explication. Le filtrage, le budget, le classement et les signaux « à vérifier » sont calculés par du code Python, testé et reproductible.

## Le trajet d'un message

```
Navigateur (HTML/JS)
   │  POST /api/chat
   ▼
FastAPI ── AgentService (le chef d'orchestre)
   │
   ├─ 0. Scout Intent (moteur Meterless) : quelle intention ? est-ce risqué ?
   │      → contrat signé qui dit quels outils ont le droit d'agir
   │      (injection ou paiement → refus ; doute → question ; comparaison/contact → autre voie)
   ├─ 1. Nemotron via Meterless : « phrase → critères » (JSON validé)
   ├─ 2. Fusion avec les critères déjà connus (mémoire de conversation)
   ├─ 3. Ville manquante ? → poser une question et s'arrêter là
   ├─ 4. Zetaris (SQL) → annonces candidates
   ├─ 5. Code : filtres obligatoires → classement → signaux à vérifier
   ├─ 6. Nemotron via Meterless : rédige l'explication à partir des seuls résultats
   └─ 7. Sauvegarde dans PostgreSQL, puis réponse JSON → cartes dans le navigateur
```

## Les trois technologies du hackathon

| Couche | Outil | Rôle dans Kwatsur |
| --- | --- | --- |
| Data | **Zetaris** (local, Docker) | Interroge les annonces en SQL. Il lit la vue `zetaris_listings` de notre base. |
| Power | **Meterless Nightshift** (appli Windows) | Fournisseur IA : notre code l'appelle, il transmet à Nemotron. |
| Modèle | **NVIDIA Nemotron 3 Ultra** | Comprend la demande et rédige l'explication. |
| Build | **Meterless Scout Intent** (`app/engines/scout/`) | Classe l'intention, bloque les demandes dangereuses et signe un contrat avant chaque action. |

PostgreSQL stocke les annonces, les conversations et les messages. Sans Zetaris ni IA, la recherche par filtres fonctionne toujours.

## Où est quoi

| Dossier | Contenu | Commencer par |
| --- | --- | --- |
| `app/api/routes/` | Les points d'entrée HTTP (minces) | `chat.py` |
| `app/services/` | La logique métier | `agent_service.py`, puis `search_service.py` |
| `app/integrations/` | Les appels externes : `llm/` (Nemotron), `agent_runtime/` (Meterless), `data/` (Zetaris, PostgreSQL) | `llm/factory.py` |
| `app/prompts/` | Les instructions données au modèle | `criteria_extraction.md` |
| `app/schemas/`, `app/models/` | Formats de données (Pydantic) et tables (SQLAlchemy) | `schemas/criteria.py` |
| `db/` | Migrations Alembic et 20 annonces **fictives** | `seed/seed_demo.py` |
| `frontend/public/` | L'interface, sans framework | `js/app.js` |
| `tests/` | Tests unitaires, d'intégration et de bout en bout, sans réseau | `e2e/test_demo_scenario.py` |

## Lancer le projet

```sh
cp .env.example .env
docker compose up --build -d                     # mode simple : PostgreSQL seul
# avec Zetaris et Nightshift en local (Docker dans WSL) :
docker compose -f docker-compose.yml -f docker-compose.wsl.yml up -d --build
```

L'interface est sur <http://localhost:8000>, ou sur le port de `API_PORT`. Pour les tests : `docker run --rm --network none -v "$PWD":/src -w /src kwatsur-api python -m pytest -q`.

Mise en place de Zetaris et Meterless : `docs/sponsor-tech.md`.

## Règles d'équipe (résumé de `AGENTS.md`)

- Ne jamais inventer de donnée. Une valeur inconnue reste `None` et s'affiche « non renseignée ».
- Une route valide l'entrée et appelle un service, rien de plus. Le SQL vit dans `repositories/`, les appels externes dans `integrations/`.
- Les noms dans le code sont en anglais et explicites ; les commentaires et l'interface sont en français.
- Aucun secret dans le code : tout passe par `.env`.
- Tout changement de table s'accompagne d'une migration Alembic.
- `pytest` doit passer avant chaque push.

## Ce qui manque encore

Voir la section 9 de `exigences.md` : mode démo sans clés, et livrables de soumission (vidéo, slides, dépôt public) avant le 27/10, 23:45 UTC.
