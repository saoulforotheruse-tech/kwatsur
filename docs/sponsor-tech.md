# Technologies sponsors : rôle réel dans Kwatsur

Ce document distingue ce qui est **implémenté et testé avec des réponses simulées** de ce qui a été **vérifié contre un vrai service**. À la date de rédaction, aucun accès sponsor n'était renseigné dans `.env` : aucune intégration n'a encore été vérifiée en conditions réelles. Mettez à jour la colonne « Vérifié » dès qu'un appel réel réussit (`GET /api/integrations/status?live=true`).

| Technologie | Rôle | Code | Vérifié en réel |
| --- | --- | --- | --- |
| NVIDIA Nemotron | Comprendre la demande, expliquer les résultats | `app/integrations/llm/` | Non (clé manquante) |
| Meterless | Exécuter Nemotron via le Meterless Runtime | `app/integrations/agent_runtime/meterless.py` | Non (runtime non installé) |
| Zetaris | Couche d'accès aux annonces (SQL via API REST) | `app/integrations/data/zetaris.py` | Non (instance non fournie) |
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
NEMOTRON_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1.5
```
Modèles Nemotron listés dans la documentation NVIDIA : `nvidia/llama-3.3-nemotron-super-49b-v1.5`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3-nano-30b-a3b`, `nvidia/nvidia-nemotron-nano-9b-v2`, etc. Choisissez-en un selon les crédits fournis.

**Données transmises.** Les critères courants, les 8 derniers messages, puis un résumé des 5 meilleurs résultats : titre, quartier, loyer, raisons, points à vérifier. Aucune coordonnée personnelle.

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
METERLESS_MODEL=meterless/auto   # remplacer par la route Nemotron listée par GET /v1/models
```
Dans Docker, l'API joint le runtime de l'hôte via `METERLESS_DOCKER_BASE_URL` (par défaut `http://host.docker.internal:8088/v1`).

**Moteurs non intégrés, et pourquoi.** H-MEM, World Model, Markovian et Scout sont publiés comme des spécifications avec une implémentation de référence en TypeScript, sans paquet Python. La mémoire de session de Kwatsur (critères et historique dans PostgreSQL) couvre le besoin du MVP. Réimplémenter un moteur aurait créé un système parallèle sans valeur démontrable dans les délais.

**Limites.** La documentation publique ne précise pas l'identifiant de route qui garantit Nemotron : il faut le lire dans `GET /v1/models` de votre runtime. L'installeur DGX était indiqué « pas encore en ligne ».

**Vérifier.** `GET /api/integrations/status?live=true` doit afficher `meterless` avec `ok`, et les messages porter la mention « Rédigé par Nemotron via Meterless ».

## Zetaris

**Rôle.** Couche d'accès aux annonces : avec `LISTING_SOURCE=zetaris`, chaque recherche du chat ou des filtres interroge Zetaris en SQL. Les lignes renvoyées sont normalisées puis filtrées et classées par le backend. PostgreSQL garde l'état applicatif : conversations, messages et import des annonces.

**API utilisée** (spécification officielle : <https://api.saas.enterprise.zetaris.com/redoc/index.html>, section « DB Query ») :
- `POST /api/v1.0/query/sql/start` avec le corps `{"select": "...", "pageLimit": 100}` ;
- `GET /api/v1.0/query/sql/page?queryToken=…&pageLimit=…&pageNumber=…` ;
- `DELETE /api/v1.0/query/sql/close/{queryToken}` ;
- en-têtes : `Authorization: Bearer <jeton API>`, `X-Request-ID` (UUID), `X-Org-ID` (entier).

**Mise en place.**
1. Exporter les annonces : `python -m scripts.export_listings_csv data/kwatsur_listings.csv` (ou `docker compose exec api python -m scripts.export_listings_csv /tmp/listings.csv`).
2. Dans Zetaris, aller dans NDP File System → `file-store`, créer un dossier puis y téléverser le CSV.
3. Dans SQL Workspace, cliquer sur « + » à côté de Virtual File Sources, créer un conteneur, ajouter le fichier depuis File Store et le nommer.
4. Vérifier la table avec l'aperçu (Preview).
5. Renseigner `.env` :
   ```env
   LISTING_SOURCE=zetaris
   ZETARIS_BASE_URL=https://<votre instance API>
   ZETARIS_API_KEY=...
   ZETARIS_ORG_ID=...
   ZETARIS_LISTINGS_TABLE=<conteneur>.<table>
   ```

**Sécurité.** L'API n'accepte pas de paramètres liés. Le nom de table est donc contrôlé par une expression régulière, et seule la ville est insérée dans la requête, après validation et échappement. Les autres filtres sont appliqués en Python.

**Limites.** La spécification ne précise pas si les pages commencent à 0 ou à 1 : le client part du `pageNumber` renvoyé. Les colonnes d'un CSV peuvent arriver sous forme de texte : elles sont converties, et une cellule vide reste inconnue. Si Zetaris est indisponible, la bascule vers PostgreSQL est affichée dans la réponse. Pour la démonstration, mettez `ZETARIS_FALLBACK_TO_POSTGRES=false` afin de prouver que les résultats viennent bien de Zetaris.

**Vérifier.** `GET /api/integrations/status?live=true` doit afficher `zetaris` avec `ok`. Les réponses du chat affichent alors « Annonces lues via Zetaris » (`data_source: "zetaris"`).

## Cursor

Cursor sert à développer, pas à exécuter l'application. Les règles de code du projet sont dans `AGENTS.md`, que Cursor lit automatiquement.
