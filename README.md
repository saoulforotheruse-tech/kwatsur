# Kwatsur

Kwatsur aide à rechercher et comparer des logements à louer au Cameroun. Ce dépôt contient un premier parcours fonctionnel avec des filtres déterministes et des annonces de démonstration clairement fictives.

## Architecture

Le projet suit quatre dossiers principaux, comme dans l’ancien projet décrit par `tree.txt` :

- [`app/`](./app/) : API FastAPI, règles métier, accès aux données et modèles.
- [`frontend/`](./frontend/) : interface web servie par l’API.
- [`docs/`](./docs/) : explications techniques et parcours de démonstration.
- [`db/`](./db/) : migrations Alembic et données de démonstration.

`tests/` et `scripts/` restent à la racine comme dossiers de support. La vue arborescente est dans [`architecture.tree`](./architecture.tree).

Une recherche suit ce parcours : le navigateur appelle une route FastAPI, la route valide les filtres, le service de recherche appelle le repository, et celui-ci interroge PostgreSQL. Le service explique ensuite les résultats et signale les informations manquantes. Le filtrage des critères obligatoires est fait par le backend, pas par une IA.

## Démarrage avec Docker

Prérequis : Docker avec Compose.

```sh
cp .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m db.seed.seed_demo
```

Ouvre ensuite <http://localhost:8000>. L’état de l’API et de la base est visible sur <http://localhost:8000/health>, et la documentation interactive de l’API sur <http://localhost:8000/docs>.

Pour arrêter les services sans effacer la base :

```sh
docker compose down
```

Les valeurs de `.env.example` ne conviennent qu’au développement local. Change les mots de passe avant tout déploiement.

## Démarrage local

Prérequis : Python 3.12 et PostgreSQL 16. Crée un environnement virtuel, installe les dépendances, configure `.env` à partir de `.env.example`, puis lance PostgreSQL.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m db.seed.seed_demo
uvicorn app.main:app --reload
```

Sur Windows, active l’environnement avec `.venv\Scripts\activate`. L’application sert l’interface et l’API sur <http://localhost:8000>.

## Recherche disponible

`GET /api/properties` accepte `city`, `neighborhood`, `min_rent`, `max_rent`, `bedrooms`, `water_available`, `electricity_available`, `furnished` et `limit`. Les équipements demandés et le nombre de chambres sont des filtres stricts. Le quartier sert de préférence de classement ; les annonces d’un autre quartier peuvent rester visibles et sont signalées. `GET /api/properties/{id}` renvoie le détail d’un logement.

Les résultats indiquent leur source, l’état de confirmation, les raisons du classement et les informations inconnues. « Non renseigné » n’est jamais converti en « non ».

## Tests

```sh
pytest
```

Les tests de recherche utilisent SQLite en mémoire ; ils ne nécessitent ni PostgreSQL ni connexion réseau.

## État des intégrations

- **PostgreSQL, SQLAlchemy et Alembic** : fondations et migration initiale en place.
- **Recherche et comparaison** : filtres backend et interface utilisables avec le seed fictif.
- **Nemotron** : non connecté ; aucune URL, clé, version de modèle ou documentation d’accès officielle n’est fournie dans le dépôt.
- **Zetaris** : non connecté ; la méthode d’accès aux données du hackathon reste à préciser.
- **Meterless** : non connecté ; les outils et instructions d’exécution requis ne sont pas présents.
- **Chat en langage naturel** : à développer après validation des accès Nemotron et du contrat de conversation.
- **Annonces réelles** : aucune source autorisée et accessible n’est configurée. Le seed ne constitue pas de vraies offres.

Les variables d’intégration sont préparées dans `.env`, mais laissées vides : aucun endpoint ni accès officiel n’est fourni dans le dépôt. Renseigne-les uniquement à partir des informations du hackathon, et ne partage jamais les clés dans le code ou le chat. Les limites et décisions d’architecture sont détaillées dans [`docs/architecture.md`](./docs/architecture.md).
