#!/bin/sh
# Démarrage du conteneur API : migrations, données fictives facultatives, puis serveur.
set -e

alembic upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python -m db.seed.seed_demo
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
