# models — rôle du dossier

Entités SQLAlchemy et relations : `Property` et `PropertySource` pour les annonces, `Conversation` et `Message` pour le contexte. Les valeurs inconnues restent nulles.

## Règles de contribution

- Les modèles décrivent la persistance et ses contraintes, pas les réponses HTTP.
- N’ajoute ni appels réseau ni logique de recherche ici.
- Chaque changement de schéma doit avoir une migration Alembic correspondante.
