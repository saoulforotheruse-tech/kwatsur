# app — rôle du dossier

Backend Python de Kwatsur. Les routes HTTP, les cas d’usage, les repositories, les modèles et les adaptateurs sont séparés dans leurs sous-dossiers.

## Règles de contribution

- Les routes dépendent des services ; les services ne dépendent pas de FastAPI.
- Les repositories seuls exécutent les requêtes de persistance.
- Les intégrations externes restent isolées et ne sont pas déclarées actives sans accès vérifié.
- Ajoute des tests aux changements de comportement.
