# services — rôle du dossier

Cas d’usage métier. `SearchService` assemble les résultats, explique leur pertinence et rend visibles les informations qui manquent ; le repository applique les filtres de recherche.

## Règles de contribution

- Le classement est déterministe : quartier préféré, nombre de détails renseignés, loyer, puis identifiant.
- N’invente ni disponibilité ni score de confiance.
- Les fournisseurs IA seront appelés via des adaptateurs une fois leurs accès vérifiés.
