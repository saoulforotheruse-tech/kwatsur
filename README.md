# Kwatsur

Kwatsur est un agent conversationnel qui aide à trouver un logement à louer au Cameroun (Douala, Yaoundé). L'utilisateur décrit son besoin en français ; l'agent extrait les critères, les mémorise, recherche dans les annonces disponibles, applique les critères obligatoires, classe les résultats de façon reproductible et explique chaque recommandation, sans jamais inventer d'information.

Projet réalisé pour l'**Open Agent Hackathon 2026** (technologies sponsors : Zetaris, NVIDIA Nemotron, Meterless, Cursor).

> Les annonces livrées avec le dépôt sont **fictives** et marquées « Démo fictive » partout.

## Ce que fait l'agent

```
« Un deux-chambres à Douala vers Bonamoussadi, 150 000 FCFA max, avec eau et électricité,
  proche des transports »
        │
        ▼
Nemotron extrait les critères (JSON validé par Pydantic) ──► mémorisés dans la conversation
        │
        ▼
Source d'annonces : Zetaris (SQL via API REST) ou PostgreSQL
        │
        ▼
Filtres obligatoires (code) → classement explicable (code) → signaux à vérifier (code)
        │
        ▼
Nemotron rédige l'explication à partir des seuls faits calculés → interface web
```

- Questions de clarification si la ville manque, recherche partielle sinon.
- Mémoire de conversation : « finalement 110 000 max » conserve la ville, les chambres, etc.
- Informations inconnues jamais converties en oui/non ; signalées « à vérifier ».
- Signaux potentiels (annonce ancienne, loyer anormalement bas, annonce peu détaillée…), jamais présentés comme une preuve d'arnaque.
- Comparaison côte à côte (3 logements) et brouillon de message de contact (aucun envoi).
- Recherche manuelle par filtres, utilisable même sans IA.
- **Meterless Scout Intent** avant chaque action : intention (recherche, comparaison, brouillon de contact), blocage des injections de prompt et des demandes de paiement, contrat signé qui autorise chaque outil. Évaluation : `python -m scripts.run_scout_evals`.

## Démarrage rapide (Docker)

Prérequis : Docker avec Compose v2.24 ou plus récent.

Kwatsur se lance en **deux parties**, chacune avec son propre `docker-compose.yml` :

| Partie | Dossier | Contenu | Adresse |
| --- | --- | --- | --- |
| Backend | racine du dépôt | PostgreSQL + API FastAPI | <http://localhost:8000> (`API_PORT`) |
| Frontend | `frontend/` | Interface servie par nginx, qui relaie `/api` vers le backend | <http://localhost:8080> (`FRONTEND_PORT`) |

```sh
# 1. Backend (migrations et données fictives appliquées au démarrage)
cp .env.example .env          # puis renseigner les clés disponibles (voir plus bas)
docker compose up --build -d

# 2. Frontend
cd frontend
cp .env.example .env          # KWATSUR_API_URL doit viser le port API_PORT du backend
docker compose up --build -d
```

- Interface : <http://localhost:8080>
- Documentation de l'API (OpenAPI) : <http://localhost:8000/docs>
- Santé : <http://localhost:8000/health>
- État des intégrations : <http://localhost:8000/api/integrations/status> (ajouter `?live=true` pour un vrai appel)

L'image du backend ne contient plus l'interface : l'API seule répond sur son port. Hors Docker (`uvicorn`), l'API sert encore `frontend/public/` pour le développement.

Si les ports 8000 ou 5432 sont déjà pris, définir dans `.env` par exemple `API_PORT=8001` et `POSTGRES_PORT=5433`, puis `KWATSUR_API_URL=http://host.docker.internal:8001` dans `frontend/.env`.

Avec Zetaris et Meterless Nightshift installés en local (Docker dans WSL en réseau `mirrored`), ajouter la surcharge qui place l'API sur le réseau de WSL, seul moyen de joindre `127.0.0.1:8888` et `127.0.0.1:8088` :

```sh
docker compose -f docker-compose.yml -f docker-compose.wsl.yml up -d --build
```

Arrêter sans effacer la base : `docker compose down` (et `docker compose down` dans `frontend/`). Repartir de zéro : `docker compose down -v`.

Diagnostic : `docker compose logs -f api` ; les erreurs des services externes y sont journalisées sans secret.

## Démarrage local (sans Docker pour l'API)

Prérequis : Python 3.12, PostgreSQL 16 (par exemple `docker compose up -d db`).

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m db.seed.seed_demo
uvicorn app.main:app --reload
```

## Configuration

Toutes les valeurs viennent de l'environnement (`.env`, jamais commité). Les secrets restent côté serveur.

| Variable | Rôle |
| --- | --- |
| `DATABASE_URL` | Connexion PostgreSQL (surchargée automatiquement dans Docker) |
| `LISTING_SOURCE` | `postgres` (défaut) ou `zetaris` |
| `ZETARIS_FALLBACK_TO_POSTGRES` | Bascule visible vers PostgreSQL si Zetaris échoue |
| `ZETARIS_BASE_URL`, `ZETARIS_API_KEY`, `ZETARIS_ORG_ID`, `ZETARIS_LISTINGS_TABLE` | Accès Zetaris (API REST officielle) |
| `LLM_PROVIDER` | `nemotron` (API NVIDIA), `meterless` (runtime local) ou `none` |
| `NEMOTRON_BASE_URL`, `NEMOTRON_API_KEY`, `NEMOTRON_MODEL` | Nemotron sur le catalogue NVIDIA |
| `METERLESS_BASE_URL`, `METERLESS_API_KEY`, `METERLESS_MODEL`, `METERLESS_APP_ID` | Nemotron via Meterless Runtime |
| `CHAT_RATE_LIMIT_PER_MINUTE` | Limite de messages par client |
| `SEED_DEMO_DATA` | Charge les annonces fictives au démarrage du conteneur |

La configuration détaillée et la vérification de chaque service sponsor sont dans [`docs/sponsor-tech.md`](./docs/sponsor-tech.md).

## Tests

```sh
pytest                         # unitaires, intégration, API et scénario de bout en bout
```

Les tests n'appellent aucun service payant ni Internet : Nemotron, Meterless et Zetaris sont remplacés par des réponses HTTP simulées (`httpx.MockTransport`) ou par `tests/fakes.py`, clairement nommés comme mocks. Le test du repository sur un vrai PostgreSQL s'active avec une base dédiée :

```sh
docker compose exec db psql -U kwatsur -c "CREATE DATABASE kwatsur_test;"
KWATSUR_TEST_DATABASE_URL=postgresql+psycopg://kwatsur:kwatsur_dev@localhost:5432/kwatsur_test pytest tests/integration/test_postgres_repository.py
```

| Dossier | Contenu |
| --- | --- |
| `tests/unit/` | critères, classement, risques, filtres, clients Nemotron/Meterless, adaptateur Zetaris |
| `tests/integration/` | agent complet (continuité, clarification, erreurs IA), endpoints, PostgreSQL réel |
| `tests/e2e/` | scénario de démonstration : demande → recherche → classement → affinage |

## Documentation

- [`docs/vue-ensemble.md`](./docs/vue-ensemble.md) : **à lire en premier**, le projet en 5 minutes.
- [`docs/exigences.md`](./docs/exigences.md) : exigences du hackathon et du produit, état de conformité, actions restantes.
- [`docs/architecture.md`](./docs/architecture.md) : couches, patterns, parcours complet d'une requête.
- [`docs/api.md`](./docs/api.md) : endpoints et contrats.
- [`docs/sponsor-tech.md`](./docs/sponsor-tech.md) : rôle réel de Zetaris, Nemotron, Meterless et Cursor.
- [`docs/data-sources.md`](./docs/data-sources.md) : provenance des données et limites.
- [`docs/demo-script.md`](./docs/demo-script.md) : scénario de démonstration (3 à 4 minutes).
- [`AGENTS.md`](./AGENTS.md) : règles de code du projet (utilisées aussi par Cursor).

## État d'avancement

**Terminé et testé**
- API FastAPI, PostgreSQL, migrations Alembic, Docker Compose avec contrôles de santé.
- Recherche : filtres obligatoires, classement explicable et configurable, signaux à vérifier, données manquantes.
- Agent : extraction des critères, fusion validée, clarification, mémoire de conversation, explication, réponse de secours étiquetée si le modèle échoue.
- Interface responsive : chat, critères retenus, cartes, comparaison, brouillon de contact, recherche manuelle.
- Client Nemotron (API NVIDIA compatible OpenAI), adaptateur Meterless, adaptateur Zetaris (API SQL REST), tous testés avec des réponses simulées.

**Implémenté mais pas encore vérifié avec un vrai service** (en attente des accès du hackathon)
- Appel réel à Nemotron : il faut `NEMOTRON_API_KEY`. Vérifier ensuite que le modèle choisi suit le format JSON demandé.
- Appel réel à Zetaris : il faut une instance, un jeton API, l'identifiant d'organisation, et la table d'annonces importée (voir `docs/sponsor-tech.md`).
- Meterless : le runtime local doit être installé et son jeton renseigné. La route qui mène à Nemotron (`METERLESS_MODEL`) doit être confirmée avec `GET /v1/models`.

**Limites connues**
- Aucune source d'annonces réelle autorisée n'est connectée : la démo repose sur des données fictives.
- La limitation de débit est stockée en mémoire, donc valable pour un seul processus.
- Il n'y a pas de comptes utilisateurs : on accède à une conversation par son identifiant aléatoire (UUID).
- La détection de préférences dans les descriptions est une simple recherche de mots-clés.
