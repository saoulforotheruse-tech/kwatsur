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

Les cartes d'annonces et leur tableau de comparaison sont regroupés sous le chat dans « Logements correspondants », un panneau natif `details` fermé par défaut et accessible au clavier. Le nombre de résultats reste visible dans son en-tête, même avec zéro résultat. Les nouvelles recherches respectent son état ouvert/fermé ; une nouvelle conversation le replie. Le bouton « Voir la comparaison » le déplie avant de rejoindre le tableau, et une erreur de recherche manuelle l'ouvre pour rester visible.

## Validation des propositions

Ouvrir `/admin.html` sur le port du frontend (par défaut `http://localhost:8080/admin.html`) et saisir le `ADMIN_TOKEN` configuré sur le backend. Sans jeton côté serveur, l'administration est fermée ; aucun jeton n'est inclus dans les fichiers frontend ni dans l'URL.

- Les propositions confirmées par « oui » dans le chat sont enregistrées dans `listing_submissions` avec le statut `pending`, sans annonce publiée.
- La page affiche les informations, photos, dates et notes ; les filtres permettent de consulter les propositions en attente, approuvées ou refusées.
- « Approuver et publier » crée une annonce dans `properties` et y rattache les photos. L'annonce reste non vérifiée, avec disponibilité à confirmer.
- « Refuser » conserve la proposition et la note sans publier d'annonce. Une décision déjà enregistrée ne peut pas être appliquée une seconde fois.
- Le jeton est mémorisé dans l'onglet après un chargement réussi. « Déconnexion » l'efface ainsi que la liste affichée. Les boutons sont désactivés pendant les requêtes pour éviter les doubles actions ; les erreurs sont affichées.

Après une modification, reconstruire le frontend (`docker compose up --build -d` dans ce dossier), puis recharger sans cache (Ctrl + F5). Une page admin vide malgré une proposition confirmée peut utiliser des modules JavaScript anciens : vérifier le filtre « En attente », le message d'erreur et l'onglet Réseau du navigateur. Ne jamais communiquer le jeton pour diagnostiquer. Une modification de `ADMIN_TOKEN` dans `.env` exige la recréation du conteneur API, pas seulement son redémarrage.

## Règles de contribution

- N’y mets ni secrets ni accès direct à PostgreSQL.
- `textContent` uniquement, jamais `innerHTML` avec des données ; textes dans `public/js/i18n/`.
- Pas de script ni de style en ligne : la CSP de nginx les bloque.
- Identité visuelle (reprise du frontend de version1.0) : polices Syne (titres) et Figtree (texte) via Google Fonts, autorisées dans la CSP ; couleurs et thème sombre définis par les variables de `public/css/styles.css`.
- Une valeur inconnue s'affiche en pointillés avec « ? », jamais comme « non ».
- Les annonces inconnues doivent rester présentées comme non renseignées.
- Vérifie les appels API et l’usage mobile après tout changement d’interface.
