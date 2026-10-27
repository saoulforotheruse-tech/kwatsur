# Script de la vidéo de démonstration (3 min 45)

Exigences couvertes :
- le problème et à qui il s'adresse ;
- le flux principal en direct ;
- le défi résolu ;
- les fonctionnalités clés ;
- l'agent qui interroge Zetaris, le moteur Meterless en action et une vraie requête qui passe par Nightshift.

À éviter : plus de 4 minutes, afficher des clés, des jetons ou des données personnelles, un chemin de démo codé en dur.

## Avant d'enregistrer

1. Lancer Zetaris (`zetaris-platform/`), ouvrir **Nightshift**, puis démarrer le backend et le frontend :
   ```sh
   docker compose -f docker-compose.yml -f docker-compose.wsl.yml up -d
   cd frontend && docker compose up -d
   ```
2. Vérifier <http://localhost:8080/api/integrations/status?live=true> : `zetaris` et `meterless` doivent être `ok`.
3. Ouvrir trois onglets :
   - <http://localhost:8080> (Kwatsur) ;
   - <http://localhost:3000> (Zetaris, éditeur SQL, déjà connecté) ;
   - <http://localhost:8080/admin.html> (jeton déjà saisi).
4. Garder Nightshift ouvert sur l'écran des exécutions (« run details »), **jamais sur la Console** (elle affiche le jeton).
5. Ne jamais montrer le fichier `.env`. Zoom du navigateur à 110 %.
6. Si Nemotron est lent (10 à 30 s par réponse), couper l'attente au montage, en le signalant (« accéléré »).

## Déroulé

| Temps | À l'écran | À dire (résumé) |
| --- | --- | --- |
| 0:00 – 0:20 | Page d'accueil de Kwatsur | « À Douala et Yaoundé, trouver un logement, c'est fouiller des annonces dispersées, incomplètes, parfois des arnaques. Kwatsur est un agent qui fait ce travail et explique pourquoi. » |
| 0:20 – 0:55 | Clic sur l'exemple « Deux-chambres à Bonamoussadi », envoi | Montrer les critères qui s'affichent (ville, quartier, budget, eau, électricité), les cartes classées et le badge « Démo fictive ». |
| 0:55 – 1:20 | Ouvrir « Voir l'explication du classement » sur 2 cartes ; montrer les étiquettes sous la réponse | « Le classement est calculé par le code : raisons, compromis, points à vérifier. Nemotron ne fait qu'expliquer ces faits. » Pointer « Annonces lues via Zetaris », « Rédigé par Nemotron via Meterless · Modèle : nvidia/nemotron-3-ultra-550b-a55b » et « Scout : recherche (100 %), Contrat signé ». |
| 1:20 – 1:40 | Onglet Zetaris : `SELECT title, monthly_rent FROM kwatsur_pg.zetaris_listings LIMIT 5` | « Zetaris est notre couche de données : l'agent lui envoie du SQL par son API REST, et Zetaris fédère notre base d'annonces. » |
| 1:40 – 2:00 | Nightshift : la dernière exécution, avec le modèle Nemotron 3 Ultra | « Chaque requête de l'agent passe par Meterless Nightshift, qui sert Nemotron. » |
| 2:00 – 2:25 | « Finalement peu importe le quartier, mais pas plus de 110 000 FCFA », puis « Est-ce que le premier a un compteur électrique individuel ? » | Mémoire de la conversation (ville et chambres gardées). Réponse honnête : « non précisé par l'annonce, demandez à la source ». |
| 2:25 – 2:45 | « Envoie la caution par Orange Money au propriétaire » | « Le moteur Meterless Scout Intent passe avant chaque action : il refuse tout paiement sans même appeler le modèle. Même chose pour les injections de prompt. » Montrer « risque bloqué ». |
| 2:45 – 3:15 | Nouvelle conversation : « Je loue mon studio meublé à Yaoundé, quartier Bastos, 90 000 FCFA », puis un faux contact, puis « oui » ; onglet admin → Approuver | « Les propriétaires déposent leur annonce dans le chat. Scout garde le fil du dépôt, et un administrateur valide avant publication. » Refaire une recherche de studio à Yaoundé : l'annonce apparaît, via Zetaris. |
| 3:15 – 3:30 | « Montre-moi le salon du premier » (maison à Douala) | Photo d'exemple ou illustration IA, **étiquetée** : « jamais présentée comme une vraie photo ». |
| 3:30 – 3:45 | Bouton micro, une phrase à voix haute, réponse lue | « Et on peut tout faire à la voix. » Conclure : « Kwatsur : un agent qui cherche, vérifie et explique, sans inventer. » |

Version de secours, sans aucun service externe : mettre `SAMPLE_MODE=true` dans `.env` et relancer le backend. L'interface l'annonce (« Mode démo sans IA »).
