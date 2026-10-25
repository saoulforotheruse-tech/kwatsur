# Scénario de démonstration (3 à 4 minutes)

Préparation :
- `docker compose up --build -d` ;
- clés Nemotron (ou Meterless) et Zetaris renseignées, `ZETARIS_FALLBACK_TO_POSTGRES=false` ;
- vérifier `http://localhost:8000/api/integrations/status?live=true`.

| Temps | Action | Ce que le jury voit |
| --- | --- | --- |
| 0:00 | Présenter le problème : annonces dispersées, incomplètes, parfois périmées. | — |
| 0:20 | Cliquer sur l'exemple « Appartement à Bonamoussadi », puis Envoyer. | Les critères extraits apparaissent en puces (ville, quartier, budget, chambres, eau, électricité, préférence). |
| 0:45 | Parcourir les cartes. | Classement n°1 à Bonamoussadi, loyers ≤ 150 000 FCFA, badge « Démo fictive », mention « Annonces lues via Zetaris », « Rédigé par NVIDIA Nemotron ». |
| 1:20 | Ouvrir « Voir l'explication du classement » sur deux cartes. | Raisons, compromis (autre quartier), points à vérifier (eau non précisée), points d'adéquation. |
| 1:45 | Montrer l'annonce d'Akwa. | Signal potentiel : loyer nettement inférieur aux annonces comparables, à vérifier avant tout paiement. |
| 2:00 | Écrire « Finalement, peu importe le quartier, mais pas plus de 100 000 FCFA ». | Le budget change, le quartier disparaît, la ville et les chambres sont conservées. Nouveaux résultats. |
| 2:30 | Cocher « Comparer » sur deux cartes. | Tableau côte à côte, valeurs inconnues affichées « Non renseigné ». |
| 2:50 | « Préparer un message ». | Brouillon de contact avec rappel : rien n'est envoyé, ne jamais payer avant une visite. |
| 3:05 | Montrer `/api/integrations/status?live=true` et `docs/sponsor-tech.md`. | Rôle réel de Zetaris, Nemotron et Meterless. |
| 3:25 | Conclure : limites (données fictives) et prochaine étape (source partenaire autorisée). | — |

Version sans réseau, reproductible : `pytest tests/e2e/test_demo_scenario.py -v` rejoue le même parcours avec un modèle simulé.
