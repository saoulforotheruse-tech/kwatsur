# Scénario de démonstration (3 à 4 minutes)

Préparation :
- backend : `docker compose up --build -d` à la racine (ou avec `docker-compose.wsl.yml`), puis frontend : `docker compose up --build -d` dans `frontend/` ; interface sur <http://localhost:8080> ;
- clés Nemotron (ou Meterless) et Zetaris renseignées ; pour une preuve strictement Zetaris, `ZETARIS_FALLBACK_TO_POSTGRES=false` ;
- vérifier `/api/integrations/status?live=true` sur le port configuré par `API_PORT` ; si Zetaris échoue, l'annoncer et montrer explicitement le repli PostgreSQL, sans revendiquer un succès sponsor ;
- reconstruire les conteneurs après les changements puis recharger sans cache ; ne jamais filmer le jeton admin ni un contact personnel.

| Temps | Action | Ce que le jury voit |
| --- | --- | --- |
| 0:00 | Présenter le problème : annonces dispersées, incomplètes, parfois périmées. | — |
| 0:20 | Cliquer sur l'exemple « Appartement à Bonamoussadi », puis Envoyer. | Les critères extraits apparaissent en puces (ville, quartier, budget, chambres, eau, électricité, préférence). |
| 0:45 | Ouvrir le panneau « Logements correspondants », fermé par défaut, puis parcourir les cartes. | Compteur visible, cartes classées et badges de provenance correspondant à la source effectivement utilisée. Pas d'image spontanée dans le chat. |
| 1:20 | Ouvrir « Voir l'explication du classement » sur deux cartes. | Raisons, compromis (autre quartier), points à vérifier (eau non précisée), points d'adéquation. |
| 1:45 | Montrer l'annonce d'Akwa. | Signal potentiel : loyer nettement inférieur aux annonces comparables, à vérifier avant tout paiement. |
| 2:00 | Écrire « Finalement, peu importe le quartier, mais pas plus de 100 000 FCFA ». | Le budget change, le quartier disparaît, la ville et les chambres sont conservées. Nouveaux résultats. |
| 2:30 | Cocher « Comparer » sur deux cartes. | Tableau côte à côte, valeurs inconnues affichées « Non renseigné ». |
| 2:50 | « Préparer un message ». | Brouillon de contact avec rappel : rien n'est envoyé, ne jamais payer avant une visite. |
| 3:05 | Si Logpom est présent : « Montre-moi les images de celui de Logpom ». | Le logement nommé est ciblé ; photo ou illustration avec étiquette. Réutilisation si disponible, génération seulement si nécessaire. |
| 3:25 | Montrer une proposition fictive déjà confirmée dans le chat puis sur `/admin.html`. | Statut en attente, aucun logement publié, décision avec note. Refuser ce test ; ne pas publier de fausse offre en base partagée. |
| 3:50 | Conclure : données fictives, sources partenaires futures. | Les appels réels et les tests hors réseau sont distingués. |

Version sans réseau, reproductible : `pytest tests/e2e/test_demo_scenario.py -v` rejoue le même parcours avec un modèle simulé.
