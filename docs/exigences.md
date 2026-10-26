# Exigences de Kwatsur et état de conformité

Document de référence : ce que le hackathon exige, ce que Kwatsur doit faire, et où chaque exigence est réalisée et testée. État au 26 octobre 2026, branche `version2.0`.

Sources :
- « Hackathon Overview » et « Participant Setup Guide » (mis à jour le 21/10/2026), sur le tableau de bord HackOS (hackathon.genai.works) ;
- spécification interne `docs/Kwatsur_specification_Zetaris_Nemotron_flux_donnees.docx` ;
- règles du dépôt `AGENTS.md`.

Légende : **Fait** (réalisé et vérifié), **Partiel** (réalisé en partie ou non vérifié en réel), **Manquant** (à faire).

## 1. Calendrier

| Étape | Date (UTC) |
| --- | --- |
| Fenêtre de développement | 22 au 27 octobre 2026 |
| **Clôture des soumissions (ferme)** | **27 octobre 2026, 23:45**, sur HackOS |
| Ouverture du jugement | 28 octobre 2026 |
| Résultats | 6 novembre 2026, 16:00 |

Le travail commité avant l'ouverture de la fenêtre n'est pas éligible, sauf composants préexistants déclarés. Le premier commit du dépôt date du 23/10/2026.

## 2. Technologies sponsors obligatoires

| # | Exigence officielle | État | Preuve dans Kwatsur |
| --- | --- | --- | --- |
| T1 | **Zetaris** est la couche de données de l'agent, installé en local (Docker). | Fait | Avec `LISTING_SOURCE=zetaris`, chaque recherche interroge Zetaris en SQL (`app/integrations/data/zetaris.py`). Zetaris fédère la vue PostgreSQL `zetaris_listings` (source `kwatsur_pg`). Vérifié le 26/10 : `/api/integrations/status?live=true` → `ok`, réponses du chat avec `data_source: "zetaris"`. |
| T2 | **Meterless Nightshift** est le fournisseur IA principal. | Fait | `LLM_PROVIDER=meterless` (`app/integrations/agent_runtime/meterless.py`) : en-têtes `meterless-app` et `meterless-scope`, découverte par `GET /v1/models`. Vérifié le 26/10 : réponses avec `reply_generated_by: "meterless"`. |
| T3 | **NVIDIA Nemotron** utilisé là où il apporte quelque chose (prix DGX Spark si Nemotron alimente réellement une fonctionnalité). | Fait | Route épinglée `nvidia/nemotron-3-ultra-550b-a55b` (`METERLESS_MODEL`). Nemotron extrait les critères et rédige l'explication. La clé NVIDIA est dans Nightshift (Providers), jamais dans le code. |
| T4 | **Au moins un Meterless Engine** (H-MEM, Markovian, World Model ou Scout) dans une fonctionnalité qui marche, **avec un test qui le prouve**. Le prompt « Add Meterless as a provider » ne suffit pas. | **Manquant** | Aucun moteur intégré. La mémoire de conversation actuelle (critères et historique dans PostgreSQL) est du code maison, pas un Meterless Engine. **Bloquant pour l'éligibilité.** |
| T5 | Cursor ou tout outil de code IA (facultatif). | Fait | `AGENTS.md` sert de règles aux agents de code. |

## 3. Livrables de soumission

| # | Livrable | État | Remarque |
| --- | --- | --- | --- |
| L1 | Vidéo de démonstration de 1 à 4 minutes : parcours principal, défi choisi, intégration Zetaris et Meterless. | Manquant | Scénario prêt : `docs/demo-script.md`. |
| L2 | Présentation (slides) : problème, utilisateurs, solution, architecture, stack, usage de Zetaris et Meterless, originalité, visuels, suites. | Manquant | Contenu disponible dans ce document et `docs/architecture.md`. |
| L3 | Dépôt GitHub **public** avec un README (installation, usage, dépendances). | Partiel | README complet. Dépôt à rendre public avant la soumission. |
| L4 | Explication des technologies sponsors : intégration Zetaris, moteur(s) Meterless et le test qui le prouve, connexion à Nightshift, apport de NVIDIA. | Partiel | `docs/sponsor-tech.md`. Il manque la partie Meterless Engine (voir T4). |
| L5 | Choix d'**un seul parcours (« track »)** principal. | Manquant | Recommandé : « The Agent That Can Explain Why » (réponses justifiées par des preuves), ou « Solving Fragmented Intelligence ». |
| L6 | Déclaration des composants préexistants. | À faire | Aucun composant antérieur au 22/10 identifié. |

## 4. Éléments qui soutiennent la note technique

| # | Élément attendu | État | Preuve ou écart |
| --- | --- | --- | --- |
| N1 | Code complet, lançable depuis une installation vierge. | Partiel | `docker compose up` suffit en mode PostgreSQL. Avec Zetaris et Nightshift : étapes manuelles documentées (rôle `zetaris_reader`, `CREATE DATASOURCE`). |
| N2 | Journaux ou traces montrant comment l'agent a abouti, **y compris quel modèle a traité chaque requête**. | Partiel | Chaque réponse indique `data_source`, `reply_generated_by` et `notices`. Le nom exact du modèle n'est ni journalisé ni renvoyé. |
| N3 | Exemples d'entrées et de sorties sur plusieurs cas. | Partiel | Tests `tests/e2e/test_demo_scenario.py` et `tests/integration/`. Pas d'exemples réels exportés pour le jury. |
| N4 | **Mode échantillon** sans Zetaris, Nightshift ni clés, pour que le jury voie l'application tourner. | Partiel | Sans clés : la recherche par filtres et l'interface fonctionnent, mais le chat renvoie une erreur 503 explicite. |
| N5 | Aucun secret commité ; `.env.example` avec des valeurs factices. | Fait | `.env`, `token.txt` et `zetaris-platform/` sont ignorés par git ; `.env.example` est vide de secrets. |

## 5. Ce que le jury valorise

| Critère du jury | Situation de Kwatsur |
| --- | --- |
| Un agent qui fait un vrai travail, sur un vrai problème | Oui : trouver un logement à Douala ou Yaoundé à partir d'une phrase, avec explication. |
| Exécution fiable, traçabilité | Oui : classement déterministe, sources affichées, réponse de secours signalée, 76 tests sans réseau. |
| Plusieurs agents qui interagissent, se critiquent ou se valident ; branchements, relances, escalade | **Faible.** Kwatsur est un seul agent au déroulé linéaire (extraire → chercher → expliquer), avec une relance si le JSON est invalide et une bascule de secours. Le jury pénalise « un seul agent présenté comme un système d'agents ». |
| Technologie sponsor au cœur, pas ajoutée à la fin | Zetaris et Nightshift sont sur le chemin de chaque requête. Le moteur Meterless manque (T4). |

## 6. Exigences fonctionnelles

| # | Exigence | État | Où c'est codé | Tests |
| --- | --- | --- | --- | --- |
| F1 | Comprendre une demande en français et en extraire des critères structurés (ville, quartier, type, budget, chambres, eau, électricité, meublé, souhaits libres). | Fait | `app/integrations/llm/nemotron.py`, prompt `app/prompts/criteria_extraction.md`, schéma `app/schemas/criteria.py` | `test_extraction_is_validated_and_retried_once`, `test_normalizes_city_type_and_preferences` |
| F2 | Valider la sortie du modèle : JSON contrôlé par Pydantic, une relance si le format est invalide. | Fait | `nemotron.py`, `criteria_service.merge_criteria` | `test_extraction_fails_cleanly_after_second_invalid_answer`, `test_merge_ignores_invalid_value_and_reports_it` |
| F3 | Mémoriser les critères d'un message à l'autre (« finalement 110 000 max » garde la ville, les chambres…). | Fait | `conversation_service.py`, `criteria_service.merge_criteria` | `test_merge_keeps_previous_criteria_when_budget_changes`, `test_conversation_keeps_criteria_and_history` |
| F4 | Poser une question si la ville manque, sans lancer de recherche. | Fait | `agent_service.handle_message` | `test_missing_city_triggers_a_question_without_search` |
| F5 | Rediriger poliment une demande hors sujet. | Fait | `agent_service.OFF_TOPIC_REPLY` | `test_off_topic_message_gets_a_redirect` |
| F6 | Appliquer les critères obligatoires dans le code, quelle que soit la source. Une valeur inconnue n'exclut pas. | Fait | `search_service.satisfies_mandatory_criteria` | `test_mandatory_filters`, `test_results_respect_every_mandatory_criterion` |
| F7 | Classer de façon reproductible et explicable : points d'adéquation, raisons, compromis, départage par loyer puis identifiant. | Fait | `ranking_service.py` (`RankingWeights` configurables) | `test_preferred_neighborhood_ranks_first_with_reason`, `test_ties_are_broken_by_rent_then_id` |
| F8 | Signaler les informations manquantes et les signaux potentiels (annonce ancienne ou non datée, loyer anormalement bas, annonce peu détaillée, absence de lien), jamais comme une preuve. | Fait | `risk_service.py` | `test_signals_never_claim_fraud`, `test_rent_far_below_comparables_is_a_potential_signal` |
| F9 | Rédiger l'explication à partir des seuls résultats calculés ; réponse de secours étiquetée si le modèle échoue. | Fait | `agent_service.summarize_for_model`, `build_template_reply` | `test_model_only_receives_verified_results`, `test_reply_failure_falls_back_to_labelled_template` |
| F10 | Proposer d'assouplir les critères quand rien ne correspond. | Fait | `criteria_service.relaxation_suggestions` | `test_no_result_proposes_relaxing_criteria` |
| F11 | Recherche manuelle par filtres, sans IA. | Fait | `GET /api/properties` | `test_property_search_filters_and_explains` |
| F12 | Comparer jusqu'à 3 logements côte à côte, inconnu affiché « Non renseigné ». | Fait | `frontend/public/js/components/property_cards.js` | Vérification manuelle |
| F13 | Brouillon de message de contact, sans aucun envoi. | Fait | `contact_service.py`, `POST /api/properties/{id}/contact-draft` | `test_property_detail_and_contact_draft` |
| F14 | Afficher l'état réel des intégrations, avec un vrai appel sur demande. | Fait | `GET /api/integrations/status?live=true` | `test_integrations_status_without_credentials` |
| F15 | Basculer vers PostgreSQL si Zetaris tombe, et le dire. | Fait | `search_service`, `ZETARIS_FALLBACK_TO_POSTGRES` | `test_falls_back_to_postgres_and_says_so` |

## 7. Exigences non fonctionnelles

| # | Exigence | État | Mise en œuvre |
| --- | --- | --- | --- |
| NF1 | **Véracité** : ne jamais inventer d'annonce, de prix, de disponibilité ni de coordonnée. Inconnu = `None`, affiché « non renseigné », jamais `False`. | Fait | Données de démonstration marquées « Démo fictive » ; conversions Zetaris : vide ou `null` → `None` (`test_rows_are_normalized_without_inventing_values`). |
| NF2 | Le modèle extrait et explique ; filtrage, budget et classement restent dans le code. | Fait | Voir F6 et F7. |
| NF3 | Architecture en couches : routes → services → repositories et intégrations ; dépendances injectées par `Depends`. | Fait | `docs/architecture.md`. |
| NF4 | Toute modification de modèle SQL passe par une migration Alembic. | Fait | `db/migrations/versions/0001…`, `0002_zetaris_listings_view`. |
| NF5 | Sécurité : aucun secret dans le code ni le frontend ; pas d'injection SQL. | Fait | Secrets dans `.env` uniquement. Le nom de table Zetaris est contrôlé par une expression régulière et la ville est validée puis échappée (`test_dangerous_text_is_refused`). Zetaris lit la base avec un rôle limité à la vue `zetaris_listings`. |
| NF6 | Frontend sans framework, `textContent` uniquement (jamais `innerHTML` avec des données). | Fait | `frontend/public/js/`. |
| NF7 | Interface et messages en français. | Fait | `frontend/public/js/i18n/fr.js`. |
| NF8 | Robustesse : délais, 401, 429 et réponses vides donnent des erreurs claires ; limite de débit du chat. | Fait | `openai_compatible.py`, `core/rate_limit.py` (`test_chat_rate_limit`). |
| NF9 | `pytest` passe sans réseau ; les mocks restent dans `tests/`. | Fait | 76 tests réussis, 2 ignorés (PostgreSQL réel, facultatif). |
| NF10 | Confidentialité : pas de compte ; les journaux ne contiennent ni messages ni secrets. | Fait | `docs/data-sources.md`. |
| NF11 | Démarrage reproductible par Docker. | Fait | `docker compose up`, plus `docker-compose.wsl.yml` avec Zetaris et Nightshift en local. |

## 8. Limites connues

- Les 20 annonces sont **fictives**. Aucune source immobilière réelle autorisée n'est encore branchée (`docs/data-sources.md`).
- La disponibilité d'un logement n'est jamais confirmée : `listing_status` reste `unconfirmed`.
- Kwatsur ne fonctionne qu'à Douala et Yaoundé, en français.

## 9. Actions prioritaires avant le 27/10, 23:45 UTC

1. **Intégrer un Meterless Engine (T4, bloquant).** Candidats naturels :
   - **Scout Intent** : router les demandes (recherche, comparaison, brouillon de contact, hors sujet) vers le bon outil ;
   - **H-MEM** : se souvenir des préférences d'une session à l'autre.

   Suivre le prompt IMPLEMENT de meterless.ai/engines.html et ajouter un test qui prouve que le moteur fonctionne.
2. **Tracer le modèle utilisé** (N2) dans chaque réponse et dans les journaux.
3. **Ajouter un mode échantillon** (N4) : par exemple un fournisseur de réponses préenregistrées, clairement étiqueté, quand `LLM_PROVIDER=none`.
4. **Envisager une étape de validation** (section 5) : un second passage de Nemotron qui vérifie que l'explication ne contient que des faits présents dans les résultats.
5. Choisir le parcours (L5), rendre le dépôt public (L3), enregistrer la vidéo (L1), faire les slides (L2) et soumettre sur HackOS.
