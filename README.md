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
- **Les propriétaires proposent leur logement dans le chat** (« je loue mon appartement… ») : l'agent pose les questions qui manquent, accepte des photos, puis envoie l'annonce à un administrateur, qui la valide sur `/admin.html` avant toute publication.
- **Résultats repliables** : cartes et comparaison sous le chat, fermées par défaut ; le compteur reste visible et la comparaison ouvre le panneau.
- **Images uniquement sur demande** (« montre-moi la douche du n°2 », « les images de celui de Logpom ») : photo du propriétaire, photo d'exemple créditée, illustration existante, puis génération Cloudflare si nécessaire. Une ambiguïté fait demander une précision. Une illustration reste étiquetée IA, jamais présentée comme une photo réelle du logement. Le contexte camerounais est réservé dans le prompt sans garantir l'apparence réelle. Voir [`docs/image-generation.md`](./docs/image-generation.md).
- **Conversation vocale** (bouton micro, Chrome ou Edge) : on parle, le texte s'écrit et part au silence, la réponse est lue à voix haute, puis l'écoute reprend. Web Speech du navigateur, sans clé.
- **Meterless Scout Intent** avant chaque action : intention (recherche, comparaison, brouillon de contact), blocage des injections de prompt et des demandes de paiement, contrat signé qui autorise chaque outil. Évaluation : `python -m scripts.run_scout_evals`.
  Par défaut (`SCOUT_ROUTING_ENABLED=false`), Scout ne classe plus l'intention : les politesses seules (« bonjour », « ça va ? », « merci ») reçoivent une réponse fixe (`app/services/small_talk.py`) et la recherche conserve le contexte pour décrire sa demande en plusieurs messages. Les demandes visuelles explicites (« génère une image de la façade du premier ») et les propositions d'annonce restent accessibles, avec garde et contrat signé. Une demande visuelle sans recherche préalable demande d'abord les critères. Comparaison et brouillon de contact demandent `SCOUT_ROUTING_ENABLED=true`.

## Démarrage rapide (Docker)

Prérequis : Docker avec Compose v2.24 ou plus récent.

Sans aucune clé, `.env.example` lance le **mode démo** : annonces fictives dans PostgreSQL, critères compris par des règles, explications générées par le code, et Scout Intent actif. Chaque réponse l'indique (« Mode démo sans IA »). Pour Zetaris, Nightshift et Nemotron, voir [`docs/sponsor-tech.md`](./docs/sponsor-tech.md).

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

## Dépendances

| Dépendance | Obligatoire ? | Rôle |
| --- | --- | --- |
| Docker + Docker Compose v2.24+ | Oui | Fait tourner PostgreSQL, l'API et le frontend (sous Windows : dans WSL 2, réseau `mirrored`) |
| **Zetaris** (plateforme locale du hackathon, Docker) | Pour le mode complet | Couche de données : les annonces sont lues en SQL via son API REST |
| **Meterless Nightshift** (application) + clé NVIDIA dans ses Providers | Pour le mode complet | Fournisseur IA principal, sert **NVIDIA Nemotron 3 Ultra** |
| Cloudflare Workers AI (compte gratuit) | Non | Illustrations d'une pièce et description des photos |
| Chrome ou Edge | Non | Conversation vocale (Web Speech) |
| Python 3.12 et `requirements.txt` (FastAPI, SQLAlchemy, Alembic, Pydantic, httpx, pytest) | Installé dans l'image Docker | Backend et tests |

Sans Zetaris, Nightshift ni Cloudflare, `SAMPLE_MODE=true` fait tourner tout le parcours (voir ci-dessous).

## Utilisation

Ouvrir <http://localhost:8080> et écrire, ou dicter avec le bouton micro :

| Exemple d'entrée | Ce que fait l'agent |
| --- | --- |
| « Je cherche un appartement de deux chambres à Douala vers Bonamoussadi, 150 000 FCFA max, avec eau et électricité » | Extrait les critères, interroge Zetaris, classe et explique les annonces |
| « Finalement peu importe le quartier, mais pas plus de 110 000 FCFA » | Garde la ville et les chambres, change le budget, relance la recherche |
| « Compare le premier et le deuxième » | Tableau comparatif ; une valeur inconnue reste « non renseignée » |
| « Est-ce que le premier a un compteur individuel ? » | Répond à partir du texte de l'annonce, ou dit que l'information manque |
| « Montre-moi le salon du premier » | Photo propriétaire ou d'exemple créditée si disponible, sinon illustration IA réutilisée ou générée, étiquetée |
| « Je loue mon studio meublé à Yaoundé, quartier Bastos, 90 000 FCFA » | Ouvre le dépôt d'annonce : questions, photos, validation sur `/admin.html` |
| « Envoie la caution par Orange Money » | Refusé par Scout Intent (aucun paiement), avec un conseil de prudence |

Les sorties réelles de ces exemples, avec leurs traces (intention, contrat, modèle utilisé), sont dans [`docs/doc_a_soumetre_pour_hackathon/fr/05_exemples_entrees_sorties.md`](./docs/doc_a_soumetre_pour_hackathon/fr/05_exemples_entrees_sorties.md). Chaque réponse de l'API contient `scout.model` (le modèle qui a traité la requête), `data_source` et `reply_generated_by` ; les journaux (`docker compose logs api`) montrent `scout.decision`, `contract.issued` et `contract.verified`.

API directe :
```sh
curl -X POST http://localhost:8080/api/chat -H "Content-Type: application/json" \
  -d '{"message": "Un studio meublé à Yaoundé, 100 000 FCFA max"}'
```

### Valider les propositions de logement

Ouvrir <http://localhost:8080/admin.html> et saisir le `ADMIN_TOKEN` configuré sur le serveur. Le panneau affiche les informations et photos des propositions, les dates, les notes et les filtres « En attente », « Approuvées » et « Refusées ».

Après confirmation « oui » du propriétaire, la proposition est conservée dans `listing_submissions` avec le statut `pending` : aucune annonce n'est encore créée dans `properties`. « Approuver et publier » crée cette annonce et y rattache les photos ; « Refuser » conserve la proposition et la décision sans publication. Une approbation ne confirme ni la disponibilité ni l'identité du propriétaire. La déconnexion efface le jeton de l'onglet.

## Mode échantillon (`SAMPLE_MODE=true`)

Si Zetaris, Nightshift ou Cloudflare sont indisponibles, mettre `SAMPLE_MODE=true` dans `.env` puis relancer le backend :
- annonces fictives de PostgreSQL ;
- critères compris par des règles ;
- explications générées par le code ;
- pas de génération d'images ;
- **Scout Intent reste actif**.

Chaque réponse l'annonce (« Mode démo sans IA »). Sans clé, `.env.example` fonctionne déjà de cette façon (`LLM_PROVIDER=rules`, `LISTING_SOURCE=postgres`).

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
| `SAMPLE_MODE` | `true` : repli complet sans Zetaris, Nightshift ni Cloudflare |
| `DATABASE_URL` | Connexion PostgreSQL (surchargée automatiquement dans Docker) |
| `LISTING_SOURCE` | `postgres` (défaut) ou `zetaris` |
| `ZETARIS_FALLBACK_TO_POSTGRES` | Bascule visible vers PostgreSQL si Zetaris échoue |
| `ZETARIS_BASE_URL`, `ZETARIS_API_KEY`, `ZETARIS_ORG_ID`, `ZETARIS_LISTINGS_TABLE` | Accès Zetaris (API REST officielle) |
| `LLM_PROVIDER` | `rules` (défaut : **mode démo sans IA ni clé**), `meterless` (Nemotron via Nightshift, utilisé pour le hackathon), `nemotron` (API NVIDIA directe) ou `none` (chat désactivé) |
| `SCOUT_SIGNING_SECRET` | Secret HMAC des contrats Scout Intent (éphémère s'il est vide) |
| `ADMIN_TOKEN` | Jeton de la page `/admin.html` qui valide les annonces proposées (vide = administration fermée) |
| `IMAGE_GENERATION_*`, `CLOUDFLARE_*` | Génération d'illustrations (voir [`docs/image-generation.md`](./docs/image-generation.md)) |
| `MEDIA_DIRECTORY`, `IMAGE_UPLOAD_MAX_BYTES` | Dossier des images (volume Docker `kwatsur_media`) et taille maximale d'une photo |
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
- [`docs/outils.md`](./docs/outils.md) : chaque outil (Zetaris, Nightshift, Nemotron, Scout, Cloudflare, PostgreSQL, Docker…), son rôle et comment y accéder.
- [`docs/exigences.md`](./docs/exigences.md) : exigences du hackathon et du produit, état de conformité, actions restantes.
- [`docs/architecture.md`](./docs/architecture.md) : couches, patterns, parcours complet d'une requête.
- [`docs/api.md`](./docs/api.md) : endpoints et contrats.
- [`docs/image-generation.md`](./docs/image-generation.md) : photos, illustrations IA, Cloudflare Workers AI.
- [`docs/sponsor-tech.md`](./docs/sponsor-tech.md) : rôle réel de Zetaris, Nemotron, Meterless et Cursor.
- [`docs/data-sources.md`](./docs/data-sources.md) : provenance des données et limites.
- [`docs/demo-script.md`](./docs/demo-script.md) : scénario de démonstration (3 à 4 minutes).
- [`AGENTS.md`](./AGENTS.md) : règles de code du projet (utilisées aussi par Cursor).

## État d'avancement (27/10/2026)

**Terminé, testé et vérifié avec les vrais services**
- **Zetaris** (local, 2.4.3) : annonces lues en SQL via l'API REST, base Kwatsur fédérée (`kwatsur_pg`).
- **Meterless Nightshift** + **NVIDIA Nemotron 3 Ultra** : extraction des critères et des annonces, explications, réponses aux questions.
- **Meterless Scout Intent** : intention, garde des risques, contrat signé avant chaque action ; évaluation au-dessus des seuils officiels.
- Recherche : filtres obligatoires, classement explicable, signaux à vérifier, mémoire de conversation, comparaison, brouillon de contact ; la ville est déduite d'un quartier connu (« Bastos » → Yaoundé) et la réponse à la question « dans quelle ville ? » poursuit la recherche.
- Dépôt d'annonces par les propriétaires dans le chat, avec photos et validation par un administrateur.
- Images : vraies photos, photos d'exemple créditées, illustrations Cloudflare FLUX.1 guidées par la vision et le contexte camerounais.
- Interface : chat, cartes illustrées, comparaison, panneaux « Mon annonce » et « Visualiser », page d'administration, conversation vocale.
- 148 tests sans réseau ; `SAMPLE_MODE` de repli ; Nemotron sans raisonnement caché (une recherche en ~15 s au lieu de ~60 s).

**Limites connues**
- Aucune source d'annonces réelle autorisée n'est encore connectée : la démo repose sur 20 annonces fictives.
- Pas de comptes utilisateurs : une conversation est accessible par son identifiant aléatoire (UUID) ; l'administration est protégée par un jeton unique.
- La limite de débit du chat est en mémoire (un seul processus) ; la limite quotidienne d'images est globale au serveur.
- La conversation vocale dépend du navigateur (Chrome ou Edge ; pas Firefox).

## Soumission au hackathon

Tout le dossier (formulaire, explication des sponsors, script vidéo, présentation, exemples) est dans [`docs/doc_a_soumetre_pour_hackathon/`](./docs/doc_a_soumetre_pour_hackathon/README.md), en français (`fr/`) et en anglais (`en/`).
