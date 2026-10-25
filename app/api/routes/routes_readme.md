# routes — rôle du dossier

Contrôleurs HTTP groupés par domaine. `properties.py` expose la recherche et le détail des logements ; `health.py` vérifie l’API et la base.

## Règles de contribution

- Valide les paramètres avant d’appeler un service.
- Délègue les recherches et transformations aux services.
- Utilise des codes HTTP adaptés et des messages compréhensibles.
