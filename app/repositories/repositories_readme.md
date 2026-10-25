# repositories — rôle du dossier

Centralise les requêtes SQLAlchemy. `PropertyRepository` applique les filtres obligatoires, exclut les annonces retirées et ordonne les résultats de façon reproductible.

## Règles de contribution

- N’y place pas les codes HTTP ni le texte de présentation des résultats.
- Utilise les paramètres validés par les schémas.
- Teste les filtres, notamment la distinction entre une valeur fausse et inconnue.
