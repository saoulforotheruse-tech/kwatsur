# db — rôle du dossier

Organisation des ressources de base de données non liées au code applicatif runtime : migrations de schéma et données d’initialisation. La connexion et les sessions utilisées par l’application restent dans `app/db/`.

## Règles de contribution

- Versionne chaque changement de schéma dans `migrations/`.
- Garde les données de seed explicites et reproductibles ; ne mets pas de secrets ni de données personnelles réelles ici.
- N’exécute pas de seed implicitement dans les environnements de production.
- Mets à jour les README des sous-dossiers si leur rôle change.
