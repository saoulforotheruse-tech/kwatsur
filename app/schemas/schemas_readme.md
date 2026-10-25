# schemas — rôle du dossier

Contrats Pydantic pour valider les critères de recherche et structurer les logements renvoyés par l’API. Ils sont distincts des modèles SQLAlchemy.

## Règles de contribution

- Valide les bornes et les longueurs à l’entrée.
- N’y ajoute pas de requêtes SQL ou de règles de classement.
- Préserve les valeurs absentes comme `None`.
