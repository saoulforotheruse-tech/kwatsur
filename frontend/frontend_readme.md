# frontend — rôle du dossier

Interface du navigateur, lancée **séparément du backend** dans son propre conteneur.

| Fichier | Rôle |
| --- | --- |
| `public/` | Page de recherche, styles et modules JavaScript (sans framework) |
| `nginx/default.conf.template` | Sert `public/`, relaie `/api` et `/health` vers le backend, ajoute les en-têtes de sécurité (CSP…) |
| `Dockerfile` | Image nginx avec l'interface |
| `docker-compose.yml` | Lance l'interface sur `FRONTEND_PORT` (8080 par défaut) |
| `public/admin.html`, `public/js/admin.js` | Page de validation des annonces proposées (jeton `ADMIN_TOKEN`) |
| `public/js/components/voice_mode.js` | Conversation vocale (Web Speech du navigateur) : écoute, envoi au silence, lecture de la réponse |
| `public/js/components/images.js` | Affichage d'une image avec son libellé : photo du propriétaire ou illustration IA |
| `.env.example` | `FRONTEND_PORT` et `KWATSUR_API_URL` (adresse du backend vue depuis le conteneur) |

```sh
cp .env.example .env
docker compose up --build -d   # interface sur http://localhost:8080
```

Le backend (racine du dépôt) doit tourner. Les appels de l'interface restent relatifs (`/api/...`) : nginx les relaie, le navigateur ne voit qu'une seule origine.

## Règles de contribution

- N’y mets ni secrets ni accès direct à PostgreSQL.
- `textContent` uniquement, jamais `innerHTML` avec des données ; textes dans `public/js/i18n/`.
- Pas de script ni de style en ligne : la CSP de nginx les bloque.
- Identité visuelle (reprise du frontend de version1.0) : polices Syne (titres) et Figtree (texte) via Google Fonts, autorisées dans la CSP ; couleurs et thème sombre définis par les variables de `public/css/styles.css`.
- Une valeur inconnue s'affiche en pointillés avec « ? », jamais comme « non ».
- Les annonces inconnues doivent rester présentées comme non renseignées.
- Vérifie les appels API et l’usage mobile après tout changement d’interface.
