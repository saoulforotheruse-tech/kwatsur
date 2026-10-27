# Technologies sponsors : rôle réel dans Kwatsur

Ce document distingue ce qui est **implémenté et testé avec des réponses simulées** de ce qui a été **vérifié contre un vrai service**. Mettez à jour la colonne « Vérifié » dès qu'un appel réel réussit (`GET /api/integrations/status?live=true`). Les accès ne sont pas fournis par le hackathon : chaque équipe installe Zetaris et Meterless Nightshift en local et crée ses clés (« Participant Setup Guide » du hackathon).

| Technologie | Rôle | Code | Vérifié en réel |
| --- | --- | --- | --- |
| NVIDIA Nemotron | Comprendre la demande, expliquer les résultats | `app/integrations/llm/` | Oui, via Meterless (26/10/2026, `nvidia/nemotron-3-ultra-550b-a55b`) |
| Meterless | Exécuter Nemotron via le Meterless Runtime | `app/integrations/agent_runtime/meterless.py` | Oui (26/10/2026, Nightshift Windows, chat de bout en bout) |
| Meterless Scout Intent | Intention, garde des risques, orientation et contrat signé avant chaque action | `app/engines/scout/` | Oui (26/10/2026, évaluation au-dessus des seuils officiels, chat réel) |
| Zetaris | Couche d'accès aux annonces (SQL via API REST) | `app/integrations/data/zetaris.py` | Oui (26/10/2026, instance locale 2.4.3, annonces lues via `kwatsur_pg.zetaris_listings`) |
| Cursor | Environnement de développement de l'équipe | `AGENTS.md` | Sans objet à l'exécution |

## NVIDIA Nemotron

**Rôle.** Deux tâches seulement :
1. extraire les critères d'un message en JSON (`app/prompts/criteria_extraction.md`) ;
2. rédiger l'explication à partir des résultats déjà filtrés et classés (`app/prompts/housing_agent.md`).

Le modèle ne filtre pas, ne calcule pas de budget et ne classe pas. Il ne reçoit aucune annonce en dehors de celles que le backend a retenues.

**Accès.** API du catalogue NVIDIA, compatible OpenAI : `POST https://integrate.api.nvidia.com/v1/chat/completions`, en-tête `Authorization: Bearer <clé>`. La clé s'obtient sur <https://build.nvidia.com>, bouton « Get API Key ».

**Configuration.**
```env
LLM_PROVIDER=nemotron
NEMOTRON_API_KEY=...
NEMOTRON_MODEL=nvidia/nemotron-3.5-bolt-e4b
```
Modèles Nemotron listés dans la documentation NVIDIA : `nvidia/nemotron-3.5-bolt-e4b`, `nvidia/nemotron-3.5-lightning-30b-a3b`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3-nano-30b-a3b`, etc. Choisissez-en un selon les crédits fournis.

**Données transmises.** Pour comprendre la demande : les critères courants et les 8 derniers messages. Pour rédiger la réponse : le message, les 8 derniers messages (pour comprendre « elle », « le premier »…) et les 5 meilleurs résultats (titre, quartier, loyer, texte de l'annonce, raisons, points à vérifier). Aucune coordonnée personnelle.

**Robustesse.** Les blocs `<think>` sont retirés. Le JSON est extrait puis validé par Pydantic, avec une relance si le format est invalide. Délai dépassé, clé refusée, quota atteint (429) et réponse vide donnent chacun un message clair. Si la rédaction échoue, une réponse générée par le code est affichée avec la mention « Réponse générée sans IA ».

**Limites.** La documentation NVIDIA consultée ne décrit pas de champ de sortie structurée (`response_format`, `guided_json`). Le format JSON est donc imposé par le prompt, puis contrôlé par Pydantic.

**Vérifier.** `curl "http://localhost:8000/api/integrations/status?live=true"` doit afficher `"status":"ok"` pour `nemotron`. Envoyez ensuite un message dans l'interface : il doit porter la mention « Rédigé par NVIDIA Nemotron ».

## Meterless

**Rôle retenu.** Le hackathon demande d'utiliser Nemotron « directement ou via Meterless ». Kwatsur prend en charge les deux chemins avec le même fournisseur (`NemotronProvider`) : seul le transport change. Le Meterless Runtime expose une API compatible OpenAI sur la machine locale.

**Ce qui est implémenté** (d'après `docs/agent-ready/add-meterless-provider.md` du dépôt public Meterless) :
- l'URL de base normalisée en `<hôte>/v1`, par défaut `http://127.0.0.1:8088/v1` ;
- `Authorization: Bearer <jeton>`, le jeton étant écrit par le runtime dans `<stateDir>/proxy-token` ;
- les en-têtes `meterless-app: kwatsur` et `meterless-scope: user` ;
- un délai d'au moins 180 s.

**Configuration.**
```env
LLM_PROVIDER=meterless
METERLESS_API_KEY=<contenu de proxy-token>
METERLESS_MODEL=nvidia/nemotron-3-ultra-550b-a55b   # route Nemotron listée par GET /v1/models
```
`meterless/auto` peut router vers un autre modèle : on épingle une route Nemotron pour que la démo prouve son usage. La clé NVIDIA se saisit dans Nightshift (Setup → Providers), jamais dans `.env`. Le jeton du Runtime se lit dans la Console de Nightshift.

**Docker dans WSL.** Nightshift tourne sous Windows et n'écoute que sur `127.0.0.1` : lancer l'API avec `docker-compose.wsl.yml` (réseau de WSL en mode `mirrored`). Sans cette surcharge, l'API tente `METERLESS_DOCKER_BASE_URL` (par défaut `http://host.docker.internal:8088/v1`), qui ne joint pas un Nightshift limité à `127.0.0.1`.

**Moteur Meterless implémenté : Scout Intent** (règle « Build », vérifié le 26/10/2026).

Scout passe avant chaque action de l'agent (`app/engines/scout/`, voir `app/engines/engines_readme.md`) :
1. **Sense** : score déterministe des intentions du catalogue `kwatsur_intents.json` (recherche, comparaison, brouillon de contact, proposition d'annonce par un propriétaire, images d'une pièce, paiement, aide générale). Les formules de politesse ne comptent que si le message ne contient rien d'autre, et « je loue mon… » ouvre le flux de proposition d'annonce, dont les messages suivants restent la suite ;
2. **Interpret** : rang du logement cité (« le n°2 »), et clarification si la confiance est basse, s'il y a égalité, si un paramètre manque ou si l'action est risquée ;
3. **Guard** : injection de prompt, politique (Kwatsur ne fait aucun paiement), portée, coordonnées personnelles ;
4. **Route** : capacités → outils (`search_service.search`, `llm.write_reply`, `comparison.build`, `contact_service.build_contact_draft`) ;
5. **Recommend** : contrat d'exécution signé (HMAC-SHA256, 5 minutes) qui désigne aussi le modèle (`nvidia/nemotron-3-ultra-550b-a55b`).

Chaque outil vérifie le contrat avant d'agir (`ContractVerifier.require`). Un contrat absent, altéré, expiré ou hors périmètre est refusé et journalisé (`contract.refused`). Sans contrat, ni le modèle ni la recherche ne sont appelés.

**Routage désactivable** (`SCOUT_ROUTING_ENABLED`, `false` par défaut depuis le 27/10/2026). Les étapes Sense et Interpret coupaient les demandes fractionnées (« 2 chambres », puis « Douala ») par des clarifications ou des redirections. Désactivé, l'agent répond en dur aux politesses seules (`app/services/small_talk.py`), impose l'intention `housing.search`, `listing.submit` pour un propriétaire ou `listing.visualize` pour une demande visuelle explicite, et appelle `ScoutEngine.authorize` : paramètres, recherche préalable, Guard, Route et Recommend s'appliquent toujours, avec contrat signé. Comparaison et brouillon de contact demandent `true`.

**Preuve.**
- `python -m scripts.run_scout_evals` : jeu de régression (47 intentions, 22 cas d'injection dont les 10 officiels de Meterless, 6 cas limites) comparé aux seuils officiels de `thresholds.yaml`. Résultat du 26/10/2026 : top-1 0,98 (plancher 0,85), top-3 1,00, précision et rappel des injections 1,00, précision des outils 1,00, taux de clarification 0,00 (plafond 0,25).
- `tests/unit/test_scout.py` et `tests/integration/test_agent_service.py` (`test_scout_*`).
- En réel : chaque réponse du chat contient `scout` (intention, confiance, risque, identifiant du contrat, outils, modèle), affiché sous la réponse. Les journaux montrent `scout.decision`, `contract.issued` et `contract.verified`.

Le lanceur officiel (`npm run evals`) attend une implémentation JavaScript : le harnais Python en reprend les métriques et les seuils. Non implémentés : Stage 2 (embeddings), plans multi-intentions, `replan`.

**Autres moteurs non intégrés.** H-MEM, World Model et Markovian ne sont pas utilisés : la mémoire de session de Kwatsur (critères et historique dans PostgreSQL) couvre le besoin.

**Limites.** La documentation publique ne précise pas l'identifiant de route qui garantit Nemotron : il faut le lire dans `GET /v1/models` de votre runtime. L'installeur DGX était indiqué « pas encore en ligne ».

**Vérifier.** `GET /api/integrations/status?live=true` doit afficher `meterless` avec `ok`, et les messages porter la mention « Rédigé par Nemotron via Meterless ».

## Zetaris

**Rôle.** Couche d'accès aux annonces : avec `LISTING_SOURCE=zetaris`, chaque recherche du chat ou des filtres interroge Zetaris en SQL. Les lignes renvoyées sont normalisées puis filtrées et classées par le backend. PostgreSQL garde l'état applicatif : conversations, messages et import des annonces.

**API utilisée** (installation locale du hackathon, version 2.4.3 ; même contrat que `scripts/zetaris_sql.py` du dépôt `zetaris/getting-started`) :
- `POST /api/v1.0/sql-editor/sqls/run` avec le corps `{"queryId": "<uuid>", "sql": "...", "source": "SqlEditor", "limit": 300}` ;
- réponse `{"headers": [colonnes], "data": [[valeurs en texte]], "total", "timeUsed"}`, en un seul appel ;
- en-têtes : `Authorization: Bearer <clé API>`, `X-Request-ID` (UUID), `X-Org-ID` (`1` en local).

En local : `ZETARIS_BASE_URL=http://127.0.0.1:8888`, `ZETARIS_ORG_ID=1`. L'API n'écoute que sur `127.0.0.1` : lancer Kwatsur avec `docker-compose.wsl.yml`.

**Mise en place retenue : Zetaris fédère la base PostgreSQL de Kwatsur** (vérifiée le 26/10/2026).
1. La migration `0002_zetaris_listings_view` crée la vue `zetaris_listings`, aux colonnes de `LISTING_COLUMNS`.
2. Créer un rôle en lecture seule sur cette vue seulement (mot de passe dans `.env` : `ZETARIS_PG_READER_PASSWORD`) :
   ```sql
   CREATE ROLE zetaris_reader LOGIN PASSWORD '<ZETARIS_PG_READER_PASSWORD>';
   GRANT CONNECT ON DATABASE kwatsur TO zetaris_reader;
   GRANT USAGE ON SCHEMA public TO zetaris_reader;
   GRANT SELECT ON zetaris_listings TO zetaris_reader;
   ```
3. Lancer Kwatsur avec `docker-compose.wsl.yml` : la base rejoint le réseau `zetaris_default` sous le nom `kwatsur-db`.
4. Dans le SQL Editor de Zetaris (une instruction à la fois) :
   ```sql
   CREATE DATASOURCE kwatsur_pg DESCRIBE BY "Kwatsur listings - PostgreSQL" OPTIONS (
     jdbcdriver "org.postgresql.Driver", jdbcurl "jdbc:postgresql://kwatsur-db:5432/kwatsur",
     username "zetaris_reader", password "<ZETARIS_PG_READER_PASSWORD>", fetchsize "1000")
   REGISTER DATASOURCE TABLE "zetaris_listings" FROM kwatsur_pg
   SELECT * FROM kwatsur_pg.zetaris_listings LIMIT 5
   ```
   La description n'accepte que lettres, chiffres, `_ . - ,` et espaces.
5. Renseigner `.env` :
   ```env
   LISTING_SOURCE=zetaris
   ZETARIS_BASE_URL=http://127.0.0.1:8888
   ZETARIS_API_KEY=<clé créée dans l'interface Zetaris>
   ZETARIS_ORG_ID=1
   ZETARIS_LISTINGS_TABLE=kwatsur_pg.zetaris_listings
   ```

Zetaris renvoie toutes les valeurs en texte, `null` pour une valeur inconnue, et les dates sans fuseau (session Spark en UTC) : l'adaptateur les relit en UTC.

**Variante CSV.** `python -m scripts.export_listings_csv data/kwatsur_listings.csv`, puis téléversement dans Zetaris (File Store → Virtual File Sources) et nom de la table dans `ZETARIS_LISTINGS_TABLE`. Non vérifiée en réel.

**Sécurité.** L'API n'accepte pas de paramètres liés. Le nom de table est donc contrôlé par une expression régulière, et seule la ville est insérée dans la requête, après validation et échappement. Les autres filtres sont appliqués en Python.

**Limites.** Les valeurs arrivent en texte : elles sont converties, et une valeur vide ou `null` reste inconnue. Si Zetaris est indisponible, la bascule vers PostgreSQL est affichée dans la réponse. Pour la démonstration, mettez `ZETARIS_FALLBACK_TO_POSTGRES=false` afin de prouver que les résultats viennent bien de Zetaris.

**Vérifier.** `GET /api/integrations/status?live=true` doit afficher `zetaris` avec `ok`. Les réponses du chat affichent alors « Annonces lues via Zetaris » (`data_source: "zetaris"`).

## Cursor

Cursor sert à développer, pas à exécuter l'application. Les règles de code du projet sont dans `AGENTS.md`, que Cursor lit automatiquement.
