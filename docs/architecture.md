# Architecture de Kwatsur

Architecture en couches inspirée de MVC, avec séparation explicite entre logique métier, accès aux données et intégrations externes.

## Couches

| Couche | Dossier | Responsabilité |
| --- | --- | --- |
| Vue | `frontend/public/` | HTML/CSS/JS sans framework. Affiche le chat et les annonces, appelle l'API via `fetch`. Aucun secret. |
| Contrôleurs | `app/api/routes/` | Valident les entrées (Pydantic), appellent un service, construisent la réponse HTTP. |
| Assemblage | `app/api/dependencies.py` | Injection de dépendances FastAPI : choisit la source d'annonces et le fournisseur IA selon la configuration. |
| Services | `app/services/` | Cas d'usage : agent, recherche, classement, risques, critères, conversations, contact. |
| Repositories | `app/repositories/` | Seul endroit où sont écrites les requêtes SQLAlchemy. |
| Intégrations | `app/integrations/` | Adaptateurs vers l'extérieur : `llm/` (Nemotron), `agent_runtime/` (Meterless), `data/` (PostgreSQL, Zetaris). |
| Modèles / schémas | `app/models/`, `app/schemas/` | Tables SQLAlchemy d'un côté, contrats Pydantic de l'autre. |
| Prompts | `app/prompts/` | Instructions données au modèle, versionnées comme du code. |

Règles de dépendance : routes → services → repositories/adaptateurs. Les services ne connaissent ni HTTP ni le frontend. Les clients externes ne sont jamais appelés depuis une route.

## Patterns utilisés et pourquoi

- **Service Layer** : `AgentService` orchestre ; `SearchService`, `RankingService`, `RiskService` restent testables séparément.
- **Repository** : `PropertyRepository`, `ConversationRepository` centralisent le SQL.
- **Adapter** : `ZetarisListingSource` et `PostgresListingSource` normalisent leurs données en `PropertyRead` ; `ChatCompletionClient` encapsule le protocole HTTP du modèle.
- **Strategy** : `ListingSource` (source d'annonces interchangeable), `LLMProvider` (fournisseur IA interchangeable), `RankingWeights` (stratégie de classement configurable).
- **Dependency Injection** : `Depends(...)` assemble les services ; les tests remplacent le fournisseur IA et la session par des doublures.

Pas d'abstraction sans usage : chaque interface a au moins deux implémentations réelles ou une doublure de test.

## Décisions importantes

1. **Le modèle comprend et explique, le code décide.** L'extraction produit un JSON validé ; le filtrage, le budget et le classement sont déterministes. Le modèle reçoit uniquement les résultats calculés pour rédiger sa réponse.
2. **Inconnu ≠ non.** Un équipement exigé n'exclut que les annonces qui le déclarent absent ; une valeur inconnue reste candidate, classée plus bas et signalée « à vérifier ».
3. **Filtrage à deux niveaux.** La source pré-filtre (SQL), puis `satisfies_mandatory_criteria` refiltre en Python toutes les annonces, quelle que soit la source. Les résultats ne dépendent donc pas du dialecte SQL de Zetaris.
4. **Points d'adéquation, pas de probabilité.** Le classement additionne des facteurs nommés (quartier, chambres, équipements confirmés, marge de budget, préférences mentionnées, fraîcheur, complétude). Départage : loyer puis identifiant, ce qui le rend reproductible.
5. **Transparence des sources.** Chaque réponse indique `data_source` (`zetaris` ou `postgres`) et `reply_generated_by` (`nemotron`, `meterless` ou `template`). Une bascule vers PostgreSQL ou une réponse sans IA est annoncée dans `notices`.
6. **Pas de faux fournisseur.** Sans clé, le chat renvoie une erreur 503 explicite. La recherche par filtres reste utilisable.

## Parcours complet d'une requête

`POST /api/chat {"message": "2 chambres à Douala vers Bonamoussadi, 150 000 max"}` :

1. `routes/chat.py` valide `ChatRequest`, applique la limite de débit et reçoit un `AgentService` injecté.
2. `AgentService.handle_message` charge ou crée la conversation via `ConversationService` → `ConversationRepository` (PostgreSQL).
3. `NemotronProvider.extract_criteria` envoie le prompt `criteria_extraction.md`, les critères actuels et l'historique récent à `ChatCompletionClient` (NVIDIA ou Meterless). La réponse JSON est validée en `CriteriaExtraction`, avec une relance si le format est invalide.
4. `merge_criteria` fusionne et valide les critères (`SearchCriteria`). Une valeur invalide est ignorée et signalée.
5. Si la ville manque, l'agent pose une question. Sinon `SearchService.search` :
   - récupère les candidats depuis la `ListingSource` configurée (Zetaris : `POST /api/v1.0/query/sql/start`, pagination, puis fermeture ; ou PostgreSQL : `PropertyRepository`) ;
   - applique les filtres obligatoires, puis `RankingService.rank` et `RiskService.assess`.
6. `NemotronProvider.write_reply` reçoit les 5 meilleurs résultats résumés (`summarize_for_model`) et le prompt `housing_agent.md`. En cas d'échec, `build_template_reply` prend le relais et l'indique.
7. `ConversationService.record_exchange` enregistre les deux messages et les critères dans une même transaction.
8. La route renvoie un `ChatResponse` : réponse, critères, résultats classés avec raisons, compromis, points à vérifier et signaux. `frontend/public/js/app.js` l'affiche : messages, puces de critères, cartes.

## Données

- `property_sources` : provenance (`is_demo`, `terms_url`, `last_sync_at`).
- `properties` : annonce ; colonnes facultatives nullables (`NULL` = inconnu), contraintes de cohérence (loyer ≥ 0, coordonnées valides), index sur ville, quartier, loyer, source.
- `conversations` : `session_id` (UUID public), `search_criteria` (JSON validé par `SearchCriteria`).
- `messages` : historique (`role`, `content`), supprimé avec la conversation.

Toute modification de modèle s'accompagne d'une migration dans `db/migrations/versions/`.
