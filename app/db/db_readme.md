# db — rôle du dossier

Accès runtime à la base : `base.py` définit la base SQLAlchemy et `session.py` crée le moteur et fournit une session par requête. Les migrations et seeds sont dans le dossier racine `db/`.

## Règles de contribution

- Ferme chaque session après usage ; l’API utilise la dépendance `get_session`.
- Laisse les requêtes métier aux repositories.
- N’ajoute pas de création automatique des tables au démarrage : Alembic gère leur évolution.
