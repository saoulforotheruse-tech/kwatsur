# Règles du projet Kwatsur

À lire par toute personne ou tout agent IA (Cursor, Claude…) qui modifie ce dépôt.

## Véracité
- Ne jamais inventer d'annonce, de prix, de disponibilité, de distance, de coordonnée ni de vérification.
- Une donnée inconnue reste `None`/`NULL` et s'affiche « non renseignée ». Elle n'est jamais convertie en `False`.
- Les signaux de risque se formulent « à vérifier » ou « signal potentiel », jamais comme une preuve.
- Ne jamais présenter une intégration comme fonctionnelle sans appel réel réussi. Les mocks vivent dans `tests/` et sont nommés comme tels.

## Architecture
- Routes (`app/api/routes`) : validation et appel d'un service, rien de plus.
- Logique métier dans `app/services`, SQL dans `app/repositories`, appels externes dans `app/integrations`.
- Le modèle IA extrait et explique ; filtrage, budget et classement restent dans le code.
- Les dépendances passent par `app/api/dependencies.py` (`Depends`), jamais par des globales mutables.
- Tout changement de modèle SQLAlchemy s'accompagne d'une migration Alembic.

## Style
- Python typé, noms explicites en anglais pour le code. Docstrings et commentaires courts en français, uniquement là où ils aident.
- Interface et messages utilisateur en français. Les textes du frontend sont dans `frontend/public/js/i18n/`.
- Frontend : JavaScript moderne sans framework, `textContent` uniquement (jamais `innerHTML` avec des données).
- Pas de secret dans le code ni dans le frontend : tout passe par `.env` (voir `.env.example`).

## Avant de livrer
- `pytest` doit passer sans réseau.
- Mettre à jour la documentation concernée (`README.md`, `docs/`).
