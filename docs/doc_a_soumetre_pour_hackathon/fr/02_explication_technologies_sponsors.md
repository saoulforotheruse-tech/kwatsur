# Explication des technologies sponsors

Toutes les intégrations ci-dessous sont **fonctionnelles et vérifiées en réel** (27/10/2026), pas seulement mentionnées. Détails techniques : `docs/sponsor-tech.md`, `docs/outils.md`, `docs/image-generation.md`.

## Zetaris — la couche de données de l'agent

**Intégration.** Zetaris tourne en local dans Docker (plateforme 2.4.3 du hackathon). Kwatsur l'utilise comme **unique point d'accès aux annonces** :
- chaque recherche (chat ou filtres) envoie une requête SQL à l'API REST de Zetaris (`POST /api/v1.0/sql-editor/sqls/run`, clé API, `X-Org-ID`, `X-Request-ID`) ;
- la réponse (`headers` et `data`) est convertie en annonces ; une valeur `null` reste « non renseignée » ;
- dans Zetaris, la base PostgreSQL de Kwatsur est enregistrée comme source fédérée (`CREATE DATASOURCE kwatsur_pg`, puis `REGISTER DATASOURCE TABLE`). Zetaris y lit la vue `zetaris_listings` avec un rôle en **lecture seule** limité à cette vue ;
- les annonces que les propriétaires proposent dans le chat, une fois validées par un administrateur, deviennent visibles via Zetaris sans autre étape.

**Rôle.** Couche de fédération et de requête : demain, d'autres sources d'annonces (API partenaires, fichiers CSV d'agences) s'ajouteront dans Zetaris sans toucher au code de l'agent.

**Preuve.**
- `GET /api/integrations/status?live=true` → `zetaris : ok`.
- Chaque réponse porte `data_source: "zetaris"`, et l'interface affiche « Annonces lues via Zetaris ».
- Journal réel : `POST http://127.0.0.1:8888/api/v1.0/sql-editor/sqls/run "HTTP/1.1 200 OK"`.
- Si Zetaris tombe, une bascule visible vers PostgreSQL est annoncée dans la réponse.

Code : `app/integrations/data/zetaris.py`, vue `db/migrations/versions/0002_zetaris_listings_view.py`.

## Meterless — moteur Scout Intent et Nightshift

### Moteur implémenté : Scout Intent

Implémentation Python de la spécification publique `engines/scout-intent` (Apache-2.0), dans `app/engines/scout/`. **Il passe avant chaque action de l'agent** :

| Étape | Ce que fait Kwatsur |
| --- | --- |
| Sense | Score déterministe des 7 intentions du catalogue : recherche, comparaison, brouillon de contact, proposition d'annonce par un propriétaire, image d'une pièce, paiement, aide générale. Autotest au démarrage : moins de 16 ms (mesuré : 0,1 ms). |
| Interpret | Paramètres liés au message (« le n°2 », « la douche »). Quatre déclencheurs de clarification : confiance basse, égalité, paramètre manquant, risque élevé. |
| Guard | Cinq couches : injection de prompt, politique (Kwatsur ne fait **aucun paiement**), portée, données personnelles, débit. |
| Route | Graphe capacités → outils : recherche, rédaction, comparaison, contact, proposition, photos, génération d'image. |
| Recommend | **Contrat d'exécution signé** (HMAC-SHA256, valable 5 minutes), qui désigne aussi le modèle. Chaque outil vérifie le contrat avant d'agir. Un contrat absent, altéré, expiré ou hors périmètre est refusé (`contract.refused`). |

**Le contrat signé, expliqué simplement.** Scout n'est pas une IA générative : c'est un moteur de règles rapide (1 ms) qui décide *avant* l'IA. Quand il accepte un message, il remet aux outils un **ticket d'autorisation** :

| Ce que dit le ticket | Exemple |
| --- | --- |
| Quelle demande il autorise | `housing.search` (une recherche) |
| Quels outils ont le droit d'agir | recherche d'annonces, rédaction de la réponse |
| Niveau de risque | `low` |
| Quel modèle traite la requête | `nvidia/nemotron-3-ultra-550b-a55b` |
| Jusqu'à quand | 5 minutes |

Le ticket est **signé** avec une clé secrète du serveur (HMAC-SHA256) : si quelqu'un modifie une seule lettre, la signature ne correspond plus. Chaque outil vérifie le ticket avant d'agir : sans ticket valide, **il refuse**. Conséquence : même si un message piégé trompait l'IA, celle-ci ne pourrait déclencher aucune action non autorisée, par exemple un paiement. Code : `app/engines/scout/contract.py`.

**Fonctionnalités qu'il porte.**
- L'aiguillage de chaque message vers la bonne voie : recherche, comparaison, contact, dépôt d'annonce, image.
- Le blocage des injections et des demandes de paiement, sans appeler le modèle.
- La continuité du dépôt d'annonce : pendant qu'un propriétaire décrit son logement, « 150 000 FCFA, 2 chambres » ou « joignable au 69… » restent sa description.

**Résultats des tests.**
- **Évaluation officielle** (seuils de `thresholds.yaml` de Meterless, jeu de régression de 59 intentions, 22 cas d'injection dont les 10 officiels, 6 cas limites) : top-1 **0,98** (plancher 0,85), top-3 **1,00**, précision et rappel des injections **1,00**, précision des outils **1,00**, clarification **0,00** (plafond 0,25). Commande : `docker exec kwatsur-api-1 python -m scripts.run_scout_evals`.
- Tests unitaires : `tests/unit/test_scout.py`, dont des contrats altérés, expirés ou hors périmètre, tous refusés.
- Tests de bout en bout : `tests/integration/test_agent_service.py`, `tests/integration/test_submissions.py`.
- **En réel**, chaque réponse du chat contient sa trace Scout (intention, confiance, risque, identifiant du contrat, outils, modèle), affichée sous la réponse, et les journaux contiennent `scout.decision`, `contract.issued` et `contract.verified`.

### Meterless Nightshift — fournisseur IA principal

Kwatsur appelle Nightshift et lui seul pour l'IA (`LLM_PROVIDER=meterless`), via son API compatible OpenAI sur `http://127.0.0.1:8088/v1` :
- jeton du Runtime lu dans la Console de Nightshift ;
- en-têtes `meterless-app: kwatsur` et `meterless-scope: user` ;
- découverte des modèles par `GET /v1/models`.

Une coupure passagère (`502 fetch failed`) est relancée une fois automatiquement. Nemotron 3 Ultra est un modèle à raisonnement : Kwatsur lui demande de répondre sans raisonnement caché (`enable_thinking=false`, réglable par `LLM_THINKING_ENABLED`), ce qui divise le temps d'un appel par environ quatre (mesuré : 26,5 s → 6,9 s pour la même extraction, résultat identique). Code : `app/integrations/agent_runtime/meterless.py`.

## NVIDIA — Nemotron via Nightshift

- **Modèle utilisé : `nvidia/nemotron-3-ultra-550b-a55b`**, épinglé dans Nightshift. `meterless/auto` pourrait router vers un autre modèle. La clé NVIDIA est enregistrée dans l'onglet *Providers* de Nightshift, jamais dans le projet.
- **Ce que fait Nemotron, dans des fonctionnalités opérationnelles** :
  - comprendre la demande et en extraire les critères en JSON validé, y compris la ville déduite d'un quartier connu (« un appart à Bastos » → Yaoundé) (prompt `criteria_extraction.md`) ;
  - comprendre la description d'un propriétaire et remplir son annonce (`listing_extraction.md`) ;
  - rédiger l'explication des résultats et répondre aux questions sur une annonce (« le premier a-t-il un compteur individuel ? »), à partir des seuls faits fournis et des 8 derniers messages (`housing_agent.md`).
- **Il ne filtre, ne classe et ne décide rien** : c'est le rôle du code.
- **Preuve du modèle utilisé** : chaque réponse indique `scout.model = "nvidia/nemotron-3-ultra-550b-a55b"` et `reply_generated_by = "meterless"`, et l'interface affiche « Rédigé par Nemotron via Meterless · Modèle : nvidia/nemotron-3-ultra-550b-a55b ». Le journal `contract.issued … profile=nvidia/nemotron-3-ultra-550b-a55b` le confirme pour chaque requête.

## Cursor (avec Space XAI) 

Le projet a été développé avec des assistants de code IA. Les règles du dépôt destinées aux agents de code (véracité, architecture, style, tests sans réseau) sont dans `AGENTS.md`, que Cursor lit automatiquement. Une partie du code a aussi été écrite avec Claude Code.

## Ce qui rend notre usage des sponsors unique

1. **Scout Intent n'est pas un ajout de façade.** Il est le garde-fou par lequel passe chaque action :
   - aucun outil n'agit sans contrat signé, et les tests prouvent que les contrats falsifiés sont refusés ;
   - il bloque les arnaques classiques du logement au Cameroun (« envoie la caution par Orange Money ») avant tout appel au modèle ;
   - il est mesuré contre les seuils officiels de Meterless.
2. **Zetaris fédère une base vivante.** Les annonces que les propriétaires déposent dans le chat, validées par un administrateur, apparaissent immédiatement dans les recherches faites via Zetaris : la couche de données reste la même quand les sources grandissent.
3. **Nemotron explique sans inventer.** Il ne reçoit que des faits vérifiés et il est contraint à ne rien inventer. Quand une information manque, il le dit (« la description ne précise pas… ; demandez-le à la source »).
4. **Fiabilité de démonstration.**
   - `SAMPLE_MODE=true` fait tourner tout le parcours sans Zetaris, Nightshift ni Cloudflare (annonces fictives, règles, Scout actif) ;
   - 148 tests passent sans réseau ;
   - les intégrations ont été vérifiées en réel.

## Technologies complémentaires (hors sponsors)

- **Cloudflare Workers AI** :
  - FLUX.1 schnell génère des **illustrations** d'une pièce quand aucune photo n'existe, avec un contexte d'habitat camerounais, toujours étiquetées « Image illustrative générée par IA » ;
  - LLaVA décrit les vraies photos pour guider ces illustrations ;
  - le fournisseur est isolé derrière une interface commune, donc remplaçable.
- **Web Speech** (navigateur) : conversation vocale ; la réponse est lue à voix haute.
