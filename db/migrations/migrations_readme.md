# migrations — rôle du dossier

Historique du schéma PostgreSQL géré par Alembic. `env.py` charge la configuration et les modèles de `app/` ; les versions sont dans `versions/`.

## Règles de contribution

- Crée les versions avec Alembic, vérifie `upgrade` et `downgrade`.
- Lance les migrations avec `alembic upgrade head`.
- N’édite pas une migration déjà appliquée : crée une nouvelle version.
