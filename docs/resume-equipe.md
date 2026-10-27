# Kwatsur — le résumé pour l'équipe (survol)

## En une phrase

Un agent qui aide à **trouver un logement à louer au Cameroun** : on lui parle (clavier ou voix), il cherche dans les annonces, les classe, explique pourquoi et dit ce qu'il faut vérifier, **sans jamais rien inventer**.

## Ce qu'on peut faire avec

- **Chercher** : « un deux-chambres à Douala, 150 000 max, avec eau ».
- **Affiner** : « finalement 110 000 max ». Il se souvient du reste.
- **Comparer** : « compare le premier et le deuxième ».
- **Poser une question** : « le premier a un compteur individuel ? ». Si l'annonce ne le dit pas, il le dit.
- **Voir une pièce** : « montre-moi la douche du n°2 ». C'est la vraie photo si elle existe, sinon une image générée par IA, toujours étiquetée.
- **Déposer son annonce** (propriétaire) : « je loue mon studio à Bastos… ». Il pose les questions qui manquent, accepte des photos, puis un administrateur valide sur `/admin.html`.
- **Parler** avec le bouton micro : la réponse est lue à voix haute.

## Comment ça marche, en 4 étapes

1. **Scout Intent** (moteur Meterless) lit le message : que veut la personne, est-ce dangereux ? Il bloque les arnaques au paiement et les tentatives de manipulation, puis donne une « autorisation signée » aux outils.
2. **Nemotron** (IA de NVIDIA, servie par **Meterless Nightshift**) comprend la phrase et en tire des critères.
3. **Zetaris** fournit les annonces (en SQL). Notre **code** filtre, classe et repère les points à vérifier.
4. **Nemotron** rédige l'explication à partir de ces seuls faits.

> Règle d'or : **l'IA comprend et explique, le code décide.**

## Les outils (où les trouver)

| Outil | Rôle | Adresse |
| --- | --- | --- |
| Interface Kwatsur | Le site | <http://localhost:8080> |
| Administration | Valider les annonces des propriétaires | <http://localhost:8080/admin.html> |
| API (et sa doc) | Le backend | <http://localhost:8001/docs> |
| Zetaris | Les données | <http://localhost:3000> |
| Nightshift | L'IA (appli Windows) | à garder ouverte |
| Cloudflare | Images générées | via le backend |

Détails : `docs/outils.md`.

## Lancer le projet

Dans le terminal WSL, dossier du projet :
```sh
docker compose -f docker-compose.yml -f docker-compose.wsl.yml up -d   # backend
cd frontend && docker compose up -d                                     # interface
```
Sans Zetaris ni Nightshift : mettre `SAMPLE_MODE=true` dans `.env` (mode démo).

## Où lire la suite

- `docs/vue-ensemble.md` : le projet en 5 minutes, avec le plan du code.
- `docs/outils.md` : chaque outil, son rôle et son accès.
- `docs/doc_a_soumetre_pour_hackathon/` : tout ce qu'on soumet au jury.

## Ce qu'il reste à faire avant 23h45 UTC

1. Enregistrer la vidéo (`docs/doc_a_soumetre_pour_hackathon/03_script_video_demo.md`).
2. Fusionner `version4.0` dans `main` (le dépôt GitHub est déjà public).
3. Soumettre sur HackOS (une seule piste, recommandée : *The Agent That Can Explain Why*).
