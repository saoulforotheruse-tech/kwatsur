# Kwatsur — architecture

Kwatsur est un agent conversationnel de recherche et de comparaison de logements à louer, conçu d’abord pour le marché camerounais.

L’architecture s’inspire de l’organisation de `tree.txt`, en l’adaptant au domaine immobilier de Kwatsur. `architecture.tree` présente la structure cible. Cette arborescence ne signifie pas que tous les modules sont déjà implémentés.

## Architecture

Le flux principal est :

`frontend/` → `app/api/routes/` → `app/services/` → `app/repositories/` et `app/integrations/`

- `app/api/` expose l’API HTTP FastAPI. Les routes valident et traduisent les requêtes, puis délèguent aux services.
- `app/services/` porte les cas d’utilisation et les règles métier. Cette couche ne dépend ni de FastAPI ni des détails de stockage.
- `app/repositories/` encapsule l’accès aux données persistées. Les modèles SQLAlchemy restent dans `app/models/`.
- `app/integrations/` isole les fournisseurs externes derrière des adaptateurs.
- `app/jobs/` accueille les tâches planifiées ou exécutées en arrière-plan. Un job délègue le travail métier aux services.
- `app/schemas/` définit les contrats d’entrée et de sortie Pydantic ; `app/core/` et `app/db/` regroupent les fondations partagées.
- `migrations/` conserve l’historique Alembic. `frontend/` contient l’interface, et `tests/` les tests unitaires, d’intégration et E2E.

Les dépendances vont vers les contrats et la logique métier, pas depuis les services vers les détails HTTP ou les SDK fournisseurs. Les dépendances concrètes sont assemblées dans l’API ou au démarrage de l’application.

## Documentation des dossiers

Chaque répertoire de code contient un fichier `<nom_du_dossier>_readme.md` décrivant son rôle et ses règles de contribution. Ces notes sont indépendantes afin que la responsabilité d’un répertoire soit compréhensible sans devoir lire toute la documentation du projet. Le script `create_kwatsur_structure.sh` crée les notes manquantes sans remplacer celles déjà présentes.

## Règles

- Garder chaque module dans sa couche et déléguer plutôt que dupliquer la logique métier.
- Ne pas inventer de données, d’endpoints ou d’intégrations.
- Marquer les données de démonstration comme fictives.
- Garder les secrets dans `.env`, jamais dans Git ni dans le frontend.
- Ajouter ou adapter les tests lors d’un changement de comportement.
- Ne déclarer un test réussi qu’après l’avoir exécuté.

## Structure

Consulte [`architecture.tree`](./architecture.tree) pour la vue arborescente et `create_kwatsur_structure.sh` pour générer le squelette dans un dossier cible. Le script conserve les fichiers existants.
