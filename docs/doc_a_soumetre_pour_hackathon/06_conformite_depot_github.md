# Conformité du dépôt GitHub

Dépôt : <https://github.com/saoulforotheruse-tech/kwatsur>

## Obligatoire

| Exigence | Où | État |
| --- | --- | --- |
| Dépôt **public** | <https://github.com/saoulforotheruse-tech/kwatsur> | Fait (vérifié le 27/10 : accessible sans connexion) |
| Tout le code source | Branche `version4.0` | **À faire** : fusionner `version4.0` dans `main` (branche affichée par défaut aux juges) |
| README : installation depuis un clone propre | README, sections « Démarrage rapide (Docker) » et « Dépendances » | Fait |
| README : utilisation avec exemples d'entrées | README, section « Utilisation » (7 exemples) | Fait |
| README : dépendances, dont Zetaris et Nightshift | README, section « Dépendances » | Fait |
| Liens Colab | — | Sans objet (aucun agent sur Colab) |

## Recommandé

| Recommandation | Où | État |
| --- | --- | --- |
| Au moins 3 exemples d'entrées et de sorties | `05_exemples_entrees_sorties.md` (6 exemples réels) | Fait |
| Journaux ou traces, y compris le modèle de chaque requête | Champ `scout` de chaque réponse (`model`, `contract_id`, `tool_plan`) ; journaux `scout.decision` et `contract.*` | Fait |
| Test démontrant le moteur Meterless | `tests/unit/test_scout.py`, `python -m scripts.run_scout_evals` (seuils officiels) | Fait |
| `.env.example` avec uniquement des valeurs de remplacement | `.env.example` | Fait (aucun secret) |
| Repli `SAMPLE_MODE=true` | `app/core/config.py` (`apply_sample_mode`), README | Fait |
| Aucune clé ni identifiant dans le dépôt | `.env`, `frontend/.env`, `token.txt`, `zetaris-platform/` et `media/` ignorés par git ; historique vérifié | Fait |
| Clé NVIDIA dans l'onglet Providers de Nightshift, pas dans le projet | `docs/outils.md`, section 3 | Fait |

## Vérification depuis un clone propre (mode échantillon)

```sh
git clone https://github.com/saoulforotheruse-tech/kwatsur.git && cd kwatsur
cp .env.example .env              # sans clé : annonces fictives, règles, Scout actif
docker compose up --build -d      # backend : migrations et 20 annonces fictives
cd frontend && cp .env.example .env && docker compose up --build -d
# → http://localhost:8080
```

Les captures d'écran WhatsApp de ce dossier (consignes de soumission) ne sont pas versionnées : ce sont des photos d'écran de téléphone.
