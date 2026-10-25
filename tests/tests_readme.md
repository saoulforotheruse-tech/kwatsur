# tests — rôle du dossier

Tests automatisés de l’API et des règles métier. `test_property_search.py` vérifie les filtres, le traitement des valeurs inconnues, les réponses HTTP et le cas logement introuvable.

## Règles de contribution

- Lance tous les tests avec `pytest` depuis la racine.
- Les tests de recherche utilisent SQLite en mémoire ; aucune API externe n’est appelée.
- Ajoute un test quand une règle de filtrage ou une réponse d’API change.
