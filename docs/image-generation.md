# Images : photos des propriétaires et illustrations IA

## Ce que fait Kwatsur

- **Photos réelles** : un propriétaire qui propose son logement dans le chat peut joindre des photos (salon, chambre, cuisine, salle de bain, façade). Elles sont publiées avec l'annonce une fois validée par un administrateur.
- **Illustrations IA** : quand quelqu'un demande « montre-moi la douche du n°2 » et qu'aucune photo de cette pièce n'existe, Kwatsur peut générer une **image illustrative** à partir du texte de l'annonce. On peut aussi en générer une depuis le panneau « Visualiser un logement ».

**Règle absolue : une illustration IA n'est jamais présentée comme une photo du logement.** Chaque image porte son type (`kind`) et un libellé visible :

| `kind` | Signification | Libellé affiché |
| --- | --- | --- |
| `owner_photo` | Photo envoyée par le propriétaire | « Photo fournie par le propriétaire » |
| `ai_generated_illustration` | Image générée par l'IA | « Image illustrative générée par IA » et « elle ne représente pas le logement réel » |
| `ai_edited_photo` | Réservé à une future retouche IA d'une vraie photo | « Photo réelle retouchée par IA » |

Kwatsur ne prétend pas reconstituer fidèlement une pièce : l'illustration montre à quoi *pourrait* ressembler un logement correspondant à la description.

## Cloudflare Workers AI et FLUX.1 schnell

- **Cloudflare Workers AI** exécute des modèles d'IA dans le cloud de Cloudflare et les expose par une API REST. Rien n'est installé sur ta machine.
- **FLUX.1 schnell** (`@cf/black-forest-labs/flux-1-schnell`) est un modèle texte → image rapide. Il accepte seulement `prompt` (1 à 2048 caractères) et `steps` (4 par défaut, 8 au maximum), et renvoie l'image encodée en base64.
- Appel : `POST https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_IMAGE_MODEL}` avec `Authorization: Bearer {CLOUDFLARE_API_TOKEN}`, toujours fait par le backend. Le jeton n'arrive jamais dans le navigateur.

Sources : [API REST](https://developers.cloudflare.com/workers-ai/get-started/rest-api/), [page du modèle](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/), [tarifs](https://developers.cloudflare.com/workers-ai/platform/pricing/).

## Parcours d'une demande

```
« Montre-moi la douche du n°2 »  ou  formulaire « Générer une image »
   │
   ▼
Scout Intent (listing.visualize) → contrat signé : images.show, images.generate
   │
   ├─ une photo du propriétaire existe pour cette pièce ? → elle est affichée
   │
   └─ sinon ImageService.generate_illustration
        1. le fournisseur est-il configuré ?           (sinon : message explicite)
        2. limite quotidienne de Kwatsur atteinte ?     (IMAGE_GENERATION_DAILY_LIMIT)
        3. prompt construit avec les seuls faits de l'annonce
        4. ImageGenerationProvider.generate_image()     (Cloudflare aujourd'hui)
        5. octets vérifiés (JPEG, PNG ou WebP), fichier écrit dans MEDIA_DIRECTORY
        6. métadonnées en base : property_images, kind = ai_generated_illustration
        7. image servie par GET /api/images/{id}
```

## Code

| Fichier | Rôle |
| --- | --- |
| `app/integrations/image_generation/base.py` | Contrat `ImageGenerationProvider`, résultat `GeneratedImage`, erreurs communes |
| `app/integrations/image_generation/cloudflare_provider.py` | Seul code qui connaît Cloudflare : requête, réponse, erreurs |
| `app/integrations/image_generation/factory.py` | Seul endroit où le fournisseur est choisi (`IMAGE_GENERATION_PROVIDER`) |
| `app/services/image_service.py` | Logique métier : limite quotidienne, prompt, enregistrement, libellés |
| `app/services/image_storage.py` | Fichiers sur disque : noms générés, signature vérifiée, taille limitée |
| `app/repositories/image_repository.py` | Métadonnées en base (table `property_images`) |
| `app/api/routes/images.py` | `GET /api/images/status`, `POST /api/images/generate`, `GET /api/images/{id}` |
| `frontend/public/js/components/images.js` | Affichage d'une image avec son libellé |

### Ajouter un autre fournisseur

1. Créer `app/integrations/image_generation/<nom>_provider.py` avec une classe qui a `name`, `model`, `is_configured` et `generate_image(prompt) -> GeneratedImage`, et qui ne lève que les erreurs de `base.py`.
2. L'ajouter dans `factory.py` sous un nom, puis mettre ce nom dans `IMAGE_GENERATION_PROVIDER`.

Rien d'autre ne change : ni les routes, ni le service, ni le stockage, ni le frontend. Un nom inconnu provoque une erreur explicite, jamais un remplacement silencieux.

## Configuration (`.env`)

| Variable | Rôle |
| --- | --- |
| `IMAGE_GENERATION_ENABLED` | `true` pour activer la génération (les photos réelles marchent dans tous les cas) |
| `IMAGE_GENERATION_PROVIDER` | `cloudflare` |
| `IMAGE_GENERATION_DAILY_LIMIT` | Images générées par jour UTC (défaut prudent : 2) |
| `CLOUDFLARE_ACCOUNT_ID` | Identifiant du compte Cloudflare |
| `CLOUDFLARE_API_TOKEN` | Jeton API Workers AI (secret) |
| `CLOUDFLARE_IMAGE_MODEL` | `@cf/black-forest-labs/flux-1-schnell` |
| `CLOUDFLARE_IMAGE_STEPS` | Étapes de diffusion, 1 à 8 (défaut 4) |
| `MEDIA_DIRECTORY` | Dossier des fichiers (`/app/media` dans Docker, volume `kwatsur_media`) |
| `IMAGE_UPLOAD_MAX_BYTES` | Taille maximale d'une photo (5 Mo) |

Sans `CLOUDFLARE_ACCOUNT_ID` ni `CLOUDFLARE_API_TOKEN`, l'application démarre normalement et affiche « La génération d'images n'est pas configurée ».

### Obtenir l'Account ID et le jeton

1. Se connecter sur <https://dash.cloudflare.com> (le compte gratuit suffit).
2. **Account ID** : Workers & Pages → « Account Details » → copier « Account ID ».
3. **Jeton** : AI → Workers AI → « Use REST API » → « Create a Workers AI API Token » → « Create API Token » → copier le jeton. Il doit avoir les permissions Workers AI (lecture et modification).
4. Coller les deux valeurs dans `.env` (jamais dans le code ni dans le chat), puis redémarrer le backend :
   ```sh
   docker compose -f docker-compose.yml -f docker-compose.wsl.yml up -d
   ```
5. Vérifier : `GET http://localhost:8080/api/images/status` doit répondre `"available": true`.

## Tester

- **Sans crédit** : `pytest tests/unit/test_image_generation.py tests/unit/test_image_service.py tests/integration/test_submissions.py`. Cloudflare y est remplacé par des réponses simulées (`httpx.MockTransport`) et par `FakeImageProvider`.
- **En réel**, une fois `.env` rempli : panneau « Visualiser un logement » → choisir « Salon », décrire la pièce → « Générer une image ». Ou bien chercher un logement, puis écrire « montre-moi la cuisine du premier ». L'image apparaît avec le badge « Illustration IA ». Le fichier est conservé dans le volume (`docker exec kwatsur-api-1 ls /app/media`), et la ligne dans `property_images`.

## Quotas et coûts

Deux limites différentes :
- **Limite de Kwatsur** (`IMAGE_GENERATION_DAILY_LIMIT`, 2 par défaut), comptée en base sur les images générées avec succès depuis minuit UTC. Elle est globale au serveur, pas par utilisateur : sans comptes utilisateurs, une limite par personne serait facile à contourner. Message : « La limite quotidienne d'images de Kwatsur est atteinte ».
- **Quota de Cloudflare** : 10 000 « neurons » gratuits par jour, remis à zéro à minuit UTC. D'après la grille tarifaire, FLUX.1 schnell coûte 4,8 neurons par tuile 512×512 et 9,6 par étape. Avec 4 étapes, cela fait environ 40 neurons par image, soit environ 230 images par jour (estimation à confirmer dans le tableau de bord). Message : « La limite du fournisseur d'images est atteinte ».

Kwatsur ne relance jamais automatiquement une génération et ne bascule jamais vers un forfait payant.

## Erreurs fréquentes

| Message | Cause probable | Solution |
| --- | --- | --- |
| « La génération d'images n'est pas configurée » | Variables Cloudflare vides, ou `IMAGE_GENERATION_ENABLED=false` | Remplir `.env`, redémarrer |
| « …a refusé les identifiants » | Jeton invalide ou sans permission Workers AI (HTTP 401/403) | Recréer le jeton avec les permissions Workers AI |
| « …ne trouve pas ce compte ou ce modèle » | Account ID ou nom de modèle erroné (HTTP 404) | Recopier l'Account ID, vérifier `CLOUDFLARE_IMAGE_MODEL` |
| « La limite du fournisseur d'images est atteinte » | Quota gratuit ou débit dépassé (HTTP 429) | Attendre minuit UTC |
| « La limite quotidienne d'images de Kwatsur est atteinte » | `IMAGE_GENERATION_DAILY_LIMIT` atteinte | Attendre demain ou augmenter la limite |
| « …momentanément indisponible » | Délai dépassé ou erreur 5xx de Cloudflare | Réessayer plus tard |
| « …réponse inexploitable » | Réponse sans image, ou contenu qui n'est pas une image | Vérifier le modèle ; les journaux du backend donnent le code d'erreur Cloudflare |

La documentation de Cloudflare ne détaille pas ses codes d'erreur : la correspondance ci-dessus repose sur les statuts HTTP standards. Les journaux du backend (`docker compose logs api`) indiquent le statut et le code d'erreur, jamais le jeton.
