# data — rôle du dossier

Emplacement des adaptateurs de sources de données : `postgres.py` (base locale), `zetaris.py` (API SQL de Zetaris) et `untera.py` (annonces internationales, utilisées hors des pays de `LOCAL_LISTING_COUNTRIES`).

## Règles de contribution

- N’utilise que des sources autorisées et documente leur provenance.
- Ne crée pas de faux client qui prétendrait interroger Zetaris.
- Normalise les données sans transformer une valeur inconnue en valeur confirmée.
