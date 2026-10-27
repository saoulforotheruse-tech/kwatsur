# Conformité du dépôt GitHub

Dépôt : <https://github.com/saoulforotheruse-tech/kwatsur>

## Obligatoire

| Exigence | Où | État |
| --- | --- | --- |
| Dépôt **public** | <https://github.com/saoulforotheruse-tech/kwatsur> | Fait (vérifié le 27/10 : accessible sans connexion) |
| Tout le code source | Branche livrée et branche par défaut | **À revérifier avant soumission** : les modifications locales doivent être publiées sur la branche présentée aux juges ; cette mise à jour documentaire ne pousse ni ne fusionne le code |
| README : installation depuis un clone propre | README, sections « Démarrage rapide (Docker) » et « Dépendances » | Fait |
| README : utilisation avec exemples d'entrées | README, section « Utilisation » (7 exemples) | Fait |
| README : dépendances, dont Zetaris et Nightshift | README, section « Dépendances » | Fait |
| Liens Colab | — | Sans objet (aucun agent sur Colab) |

## Recommandé

| Recommandation | Où | État |
| --- | --- | --- |
| Au moins 3 exemples d'entrées et de sorties | `05_exemples_entrees_sorties.md` (7 exemples historiques et compléments vérifiés) | Fait ; les conditions de routage et de repli sont précisées |
| Journaux ou traces, y compris le modèle de chaque requête | Champ `scout` de chaque réponse (`model`, `contract_id`, `tool_plan`) ; journaux `scout.decision` et `contract.*` | Fait |
| Test démontrant le moteur Meterless | `tests/unit/test_scout.py`, `python -m scripts.run_scout_evals` (seuils officiels) | Fait |
| `.env.example` avec uniquement des valeurs de remplacement | `.env.example` | Fait (aucun secret) |
| Repli `SAMPLE_MODE=true` | `app/core/config.py` (`apply_sample_mode`), README | Fait |
| Aucune clé ni identifiant dans le dépôt | `.env`, `frontend/.env`, `token.txt`, `zetaris-platform/` et `media/` ignorés par git ; historique vérifié | Fait |
| Clé NVIDIA dans l'onglet Providers de Nightshift, pas dans le projet | `docs/outils.md`, section 3 | Fait |

## Vérification depuis un clone propre (mode échantillon)

Couverture récente hors réseau : **214 tests réussis, 2 ignorés**, notamment persistance des propositions, absence de publication en attente, authentification, décisions et rattachement des photos. Les présentations FR/EN incluent le dépôt et le panneau admin avec contacts anonymisés. Les captures ne constituent pas une preuve d'approbation réelle.

```sh
git clone https://github.com/saoulforotheruse-tech/kwatsur.git && cd kwatsur
cp .env.example .env              # sans clé : annonces fictives, règles, Scout actif
docker compose up --build -d      # backend : migrations et 20 annonces fictives
cd frontend && cp .env.example .env && docker compose up --build -d
# → http://localhost:8080
```

Les captures d'écran WhatsApp des consignes de soumission (dossier parent) ne sont pas versionnées : ce sont des photos d'écran de téléphone.
