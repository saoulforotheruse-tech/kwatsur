# db — rôle du dossier

Migrations PostgreSQL et données d’initialisation. La connexion utilisée par l’API reste dans `app/db/`.

## En pratique

- `migrations/versions/` garde l’historique du schéma ; exécute-le avec `alembic upgrade head`.
- `seed/seed_demo.py` ajoute trois annonces fictives et peut être relancé sans doublons.
- Les seeds ne sont pas lancés automatiquement en production. N’ajoute ici ni secret ni donnée personnelle réelle.
