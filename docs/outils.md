# Les outils de Kwatsur : rôle et accès

Pour chaque outil : **à quoi il sert dans Kwatsur**, **comment y accéder** et **où il apparaît dans le code**. Les adresses et ports sont ceux de l'installation de l'équipe : Docker dans WSL, ports changés à cause d'un autre projet. Les valeurs par défaut sont données entre parenthèses.

Les secrets (clés, jetons, mots de passe) sont **uniquement dans `.env`**, jamais dans le code, ce document ou le chat. `.env.example` liste les variables sans valeur.

## Vue d'ensemble

| Couche | Outil | Rôle en une phrase | Accès principal |
| --- | --- | --- | --- |
| Données (hackathon) | **Zetaris** | Interroge les annonces en SQL | <http://localhost:3000> (interface), `127.0.0.1:8888` (API) |
| IA (hackathon) | **Meterless Nightshift** | Fournisseur IA principal, relaie vers Nemotron | Application Windows, `127.0.0.1:8088` |
| Modèle (hackathon) | **NVIDIA Nemotron** | Comprend les demandes et rédige les réponses | Via Nightshift (clé NVIDIA dans Nightshift) |
| Moteur (hackathon) | **Meterless Scout Intent** | Décide, contrôle et autorise chaque action | Code : `app/engines/scout/` |
| Images | **Cloudflare Workers AI** (FLUX.1 schnell) | Génère des illustrations de pièces | API Cloudflare, appelée par le backend |
| Base | **PostgreSQL 16** | Stocke annonces, conversations, propositions, images | `localhost:5433` (5432) |
| Backend | **FastAPI** + Uvicorn | API HTTP de Kwatsur | <http://localhost:8001> (8000), doc sur `/docs` |
| Frontend | **nginx** + HTML/CSS/JS | Interface web | <http://localhost:8080> |
| Lancement | **Docker Compose** dans **WSL** | Fait tourner tous les conteneurs | Terminal Ubuntu (WSL) |
| Qualité | **pytest** | Tests sans réseau | Dans le conteneur `kwatsur-api` |
| Code | **Git / GitHub**, **Cursor** | Versions et développement | <https://github.com/saoulforotheruse-tech/kwatsur> |

---

## 1. Zetaris — la couche de données

**Rôle.** Plateforme de fédération de données, imposée par le hackathon. Kwatsur ne lit pas les annonces directement : il envoie une requête SQL à Zetaris, qui interroge la vue `zetaris_listings` de notre PostgreSQL (source enregistrée sous le nom `kwatsur_pg`). Les annonces approuvées par un administrateur y apparaissent automatiquement.

**Accès.**
- Installation locale dans Docker (dossier `zetaris-platform/`, ignoré par git). Démarrer : `cd zetaris-platform && docker compose up -d`. Vérifier : `./verify.sh` (9 contrôles).
- Interface et éditeur SQL : <http://localhost:3000>, avec le compte administrateur défini dans `zetaris-platform/.env` (`ZETARIS_ADMIN_EMAIL`, `ZETARIS_ADMIN_PASSWORD`).
- API REST : `http://127.0.0.1:8888/api/v1.0`, accessible seulement depuis la machine. Une requête = `POST /sql-editor/sqls/run` avec `Authorization: Bearer <clé>`, `X-Org-ID: 1` et `X-Request-ID` (UUID).
- La **clé API** se crée dans l'interface Zetaris, pour votre utilisateur. Elle n'est affichée qu'une fois. Le guide du hackathon demande de la créer soi-même, sans agent IA.
- Compte cloud (pour télécharger la plateforme) : <https://cloud.enterprise.zetaris.com>.

**Configuration (`.env`).** `LISTING_SOURCE=zetaris`, `ZETARIS_BASE_URL=http://127.0.0.1:8888`, `ZETARIS_API_KEY`, `ZETARIS_ORG_ID=1`, `ZETARIS_LISTINGS_TABLE=kwatsur_pg.zetaris_listings`, `ZETARIS_PG_READER_PASSWORD` (rôle PostgreSQL en lecture seule utilisé par Zetaris), `ZETARIS_FALLBACK_TO_POSTGRES`.

**Code.** `app/integrations/data/zetaris.py`. Mise en place détaillée : `docs/sponsor-tech.md`.

**Vérifier.** <http://localhost:8001/api/integrations/status?live=true> → `zetaris : ok`. Les réponses du chat affichent « Annonces lues via Zetaris ».

## 2. Meterless Nightshift — le fournisseur IA

**Rôle.** « Hotspot » IA installé sur l'ordinateur, imposé comme fournisseur principal. Kwatsur ne parle jamais directement à NVIDIA : il appelle Nightshift (API compatible OpenAI), qui transmet au modèle choisi.

**Accès.**
- Application Windows, téléchargée sur <https://www.meterless.ai> (accès par e-mail). Elle doit être **ouverte** pendant l'utilisation de Kwatsur.
- **Console** (en haut à droite de Nightshift) : donne l'URL du Runtime et le **jeton** à mettre dans `.env`.
- API locale : `http://127.0.0.1:8088/v1`. Elle n'est joignable que depuis la machine, d'où le lancement du backend avec `docker-compose.wsl.yml`.
- Liste des modèles disponibles : `GET /v1/models` avec le jeton.

**Configuration (`.env`).** `LLM_PROVIDER=meterless`, `METERLESS_BASE_URL=http://127.0.0.1:8088/v1`, `METERLESS_API_KEY` (jeton de la Console), `METERLESS_MODEL=nvidia/nemotron-3-ultra-550b-a55b`, `METERLESS_APP_ID=kwatsur`.

**Code.** `app/integrations/agent_runtime/meterless.py` et `app/integrations/llm/openai_compatible.py` (une relance automatique si Nightshift répond 502/503).

## 3. NVIDIA Nemotron — le modèle de langage

**Rôle.** Comprend les messages (critères de recherche, informations d'annonce d'un propriétaire) et rédige les explications à partir des seuls faits calculés par le code. **Il ne filtre, ne classe et ne décide rien.**

**Accès.**
- Clé API sur <https://build.nvidia.com/models>, à coller dans **Nightshift → Setup → Providers → NVIDIA**, jamais dans `.env` de Kwatsur.
- Modèle épinglé : `nvidia/nemotron-3-ultra-550b-a55b`. `meterless/auto` pourrait router vers un autre modèle.
- Mode direct sans Nightshift (secours) : `LLM_PROVIDER=nemotron`, `NEMOTRON_API_KEY`, `NEMOTRON_MODEL`.

**Code.** `app/integrations/llm/nemotron.py`, prompts dans `app/prompts/` (`criteria_extraction.md`, `listing_extraction.md`, `housing_agent.md`).

**Vérifier.** Sous chaque réponse du chat : « Rédigé par Nemotron via Meterless · Modèle : nvidia/nemotron-3-ultra-550b-a55b ».

## 4. Meterless Scout Intent — le moteur de décision

**Rôle.** Moteur Meterless exigé par le hackathon (règle « Build »). Il passe **avant chaque action** :
1. il reconnaît l'intention (recherche, comparaison, contact, proposition d'annonce, image d'une pièce, paiement, aide) ;
2. il bloque les injections de prompt et les paiements ;
3. il pose une question en cas de doute ;
4. il signe un **contrat** qui autorise des outils précis. Chaque outil vérifie ce contrat avant d'agir.

**Accès.** Ce n'est pas un service à part : c'est du code Python dans Kwatsur (`app/engines/scout/`), écrit d'après la spécification publique <https://github.com/Meterless/Meterless> (`engines/scout-intent/`).
- Catalogue des intentions : `app/engines/scout/kwatsur_intents.json`.
- Évaluation officielle : `python -m scripts.run_scout_evals`, à lancer dans le conteneur.
- Trace visible sous chaque réponse (« Scout : recherche (100 %), risque faible · Contrat signé … ») et dans les journaux (`scout.decision`, `contract.issued`, `contract.verified`).

**Configuration.** `SCOUT_SIGNING_SECRET` (secret de signature des contrats).

## 5. Cloudflare Workers AI — la génération d'images

**Rôle.** Génère une **image illustrative** d'une pièce (salon, douche, façade…) quand le propriétaire n'a pas fourni de photo. Modèle : FLUX.1 schnell. L'image est toujours étiquetée « générée par IA », jamais présentée comme une photo.

**Accès.**
- Compte gratuit sur <https://dash.cloudflare.com>.
  - **Account ID** : Workers & Pages → Account Details.
  - **Jeton** : AI → Workers AI → « Use REST API » → « Create a Workers AI API Token ».
- Appelé uniquement par le backend : `POST https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/@cf/black-forest-labs/flux-1-schnell`.
- Quota gratuit : 10 000 « neurons » par jour, soit environ 230 images ; limite de Kwatsur : 2 par jour par défaut.

**Configuration (`.env`).** `IMAGE_GENERATION_ENABLED`, `IMAGE_GENERATION_PROVIDER=cloudflare`, `IMAGE_GENERATION_DAILY_LIMIT`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_IMAGE_MODEL`, `CLOUDFLARE_IMAGE_STEPS`.

**Code.** `app/integrations/image_generation/`, accessible uniquement par l'interface commune. Détails : `docs/image-generation.md`.

**Vérifier.** <http://localhost:8080/api/images/status> → `"available": true`.

## 6. PostgreSQL — la base de données

**Rôle.** Stocke :
- les annonces et leurs sources (`properties`, `property_sources`) ;
- les conversations et leurs messages (`conversations`, `messages`) ;
- les propositions des propriétaires (`listing_submissions`) ;
- les métadonnées des images (`property_images`).

Les fichiers image sont sur le disque (volume `kwatsur_media`).

**Accès.**
- Conteneur `kwatsur-db-1`. Console SQL :
  ```sh
  docker exec -it kwatsur-db-1 psql -U kwatsur -d kwatsur
  ```
- Depuis un outil graphique (DBeaver, pgAdmin) : `localhost:5433` (5432), base `kwatsur`, utilisateur `POSTGRES_USER`, mot de passe `POSTGRES_PASSWORD` de `.env`.
- Zetaris s'y connecte avec le rôle en lecture seule `zetaris_reader`, limité à la vue `zetaris_listings`.

**Code.** Modèles : `app/models/` ; requêtes : `app/repositories/` ; données fictives : `db/seed/seed_demo.py`.

## 7. Alembic — l'évolution de la base

**Rôle.** Applique les changements de structure de la base dans l'ordre (`0001` schéma initial, `0002` vue pour Zetaris, `0003` propositions et images). La règle du projet : tout changement de modèle s'accompagne d'une migration.

**Accès.** Automatique au démarrage du conteneur API (`alembic upgrade head` dans `scripts/docker-entrypoint.sh`). Version actuelle :
```sh
docker exec kwatsur-db-1 psql -U kwatsur -d kwatsur -c "select version_num from alembic_version"
```
**Code.** `db/migrations/versions/`.

## 8. FastAPI et Uvicorn — le backend

**Rôle.** FastAPI expose l'API HTTP : chat, recherche, images, propositions, administration. Uvicorn est le serveur qui l'exécute. Les routes ne font que valider et appeler un service ; la logique est dans `app/services/`.

**Accès.**
- <http://localhost:8001> (`API_PORT`, 8000 par défaut).
- **Documentation interactive de l'API** : <http://localhost:8001/docs> (Swagger) et `/redoc`.
- Santé : <http://localhost:8001/health>. Journaux : `docker compose logs -f api`.

**Bibliothèques associées.**
- **Pydantic** : valide toutes les données (`app/schemas/`).
- **SQLAlchemy** : dialogue avec PostgreSQL.
- **httpx** : appels à Zetaris, Nightshift et Cloudflare.
- **pydantic-settings** : lit `.env` (`app/core/config.py`).

## 9. Frontend et nginx — l'interface web

**Rôle.**
- **Interface** : HTML, CSS et JavaScript sans framework (`frontend/public/`). On y trouve le chat, les annonces, la comparaison, le panneau « Mon annonce proposée », le panneau « Visualiser un logement » et la page d'administration.
- **nginx** : sert ces fichiers et relaie `/api` et `/health` vers le backend. Le navigateur ne voit qu'une seule adresse, donc pas de problème de CORS.

**Accès.**
- Interface : <http://localhost:8080> (`FRONTEND_PORT`).
- **Administration des annonces** : <http://localhost:8080/admin.html>, avec le jeton `ADMIN_TOKEN` de `.env`.
- Lancement : `cd frontend && docker compose up -d --build`. L'adresse du backend vue par nginx est dans `frontend/.env` (`KWATSUR_API_URL=http://host.docker.internal:8001`).
- Polices Syne et Figtree chargées depuis **Google Fonts** (autorisé dans la politique de sécurité de nginx).

**Voix.** Le bouton micro utilise l'API Web Speech du navigateur (Chrome, Edge) : reconnaissance vocale en `fr-FR` et lecture à voix haute. La réponse est lue par morceaux de 150 caractères au plus, car Chrome coupe sans prévenir ses voix en ligne (« Google français ») après environ 15 s. La lecture est autorisée par le clic sur le micro (sinon Chrome répond `not-allowed`). En cas de souci, ouvrir la console (F12) et chercher `[Kwatsur voix]`. Aucune clé, mais il faut autoriser le micro dans le navigateur (cadenas de la barre d'adresse). Firefox ne propose pas la reconnaissance vocale : le bouton y est masqué.

**Code.** `frontend/public/js/app.js` (point d'entrée), `components/` (chat, cartes, images, annonce), `i18n/fr.js` (tous les textes), `frontend/nginx/default.conf.template`.

## 10. Docker, Docker Compose et WSL — le lancement

**Rôle.** Tout tourne en conteneurs, dans **WSL (Ubuntu)** sous Windows, en réseau `mirrored` (`%USERPROFILE%\.wslconfig`). Trois projets Compose indépendants :

| Projet | Dossier | Conteneurs |
| --- | --- | --- |
| Zetaris | `zetaris-platform/` | postgres, driver, api, ui |
| Backend Kwatsur | racine | `kwatsur-db-1`, `kwatsur-api-1` |
| Frontend Kwatsur | `frontend/` | `kwatsur-frontend-web-1` |

**Accès (dans le terminal WSL, depuis `/mnt/f/shared_folder/kwatsur`).**
```sh
# Backend (avec Zetaris et Nightshift en local)
docker compose -f docker-compose.yml -f docker-compose.wsl.yml up -d --build
# Frontend
cd frontend && docker compose up -d --build
# État et journaux
docker ps
docker compose logs -f api
```
`docker-compose.wsl.yml` place l'API sur le réseau de WSL : c'est le seul moyen de joindre Zetaris (`127.0.0.1:8888`) et Nightshift (`127.0.0.1:8088`). Sans clé (mode démo), `docker compose up -d --build` seul suffit.

## 11. pytest — les tests

**Rôle.** Plus de 130 tests automatiques, sans réseau : Zetaris, Nightshift et Cloudflare y sont simulés (`tests/fakes.py`, `httpx.MockTransport`). Ils doivent passer avant chaque push.

**Accès.**
```sh
docker run --rm --network none -v "$PWD":/src -w /src kwatsur-api python -m pytest -q
```
Unitaires dans `tests/unit/`, intégration dans `tests/integration/`, scénario de démo dans `tests/e2e/`.

## 12. Git, GitHub et Cursor — le développement

- **GitHub** : <https://github.com/saoulforotheruse-tech/kwatsur>. Une branche par étape (`version1.0` … `version3.3`, `version4.0`) ; `main` reçoit les versions stables.
- **Fins de ligne** : `.gitattributes` force LF pour les scripts et la configuration nginx.
- **Ignoré par git** : `.env`, `frontend/.env`, `token.txt`, `zetaris-platform/`, `media/`.
- **Cursor**, ou un autre outil de code IA : sert à développer, pas à faire tourner Kwatsur. Les règles du projet pour les agents de code sont dans `AGENTS.md`.

## Mode démo sans aucun de ces services externes

Avec `LISTING_SOURCE=postgres` et `LLM_PROVIDER=rules` (les valeurs de `.env.example`), Kwatsur tourne avec **Docker seul** :
- annonces fictives dans PostgreSQL ;
- critères compris par des règles ;
- explications générées par le code ;
- Scout toujours actif.

C'est le mode à utiliser par le jury ou par un collaborateur qui n'a pas les clés.
