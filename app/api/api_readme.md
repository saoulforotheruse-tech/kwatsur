# api — rôle du dossier

Couche HTTP FastAPI. `dependencies.py` fournit les sessions et services aux routes, qui valident les paramètres et traduisent les réponses en contrats d’API.

## Règles de contribution

- Ne place pas de requêtes SQL ou de règles métier dans les routes.
- Retourne des erreurs HTTP claires sans exposer les détails internes.
- Couvre les routes par des tests sans dépendance à un service externe.
