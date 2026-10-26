# engines — moteurs Meterless

Implémentations Python des moteurs Meterless utilisés par Kwatsur (règle « Build » du hackathon : au moins un moteur dans une fonctionnalité qui marche).

## scout/ — Meterless Scout Intent

Passe **avant chaque action** de l'agent : classe l'intention du message, contrôle les risques, choisit les outils et signe un contrat d'exécution. Aucun outil n'agit sans contrat valide.

| Fichier | Étape de la spécification |
| --- | --- |
| `kwatsur_intents.json`, `registry.py` | Catalogue des intentions (seules ces intentions peuvent agir) |
| `sense.py` | Sense : score déterministe par mots déclencheurs, bandes de confiance, autotest de 16 ms |
| `interpret.py` | Interpret : rangs cités (« le n°2 »), 4 déclencheurs de clarification |
| `guard.py` | Guard : injection, politique (pas de paiement), portée, données personnelles, débit |
| `engine.py` | Route (graphe capacités → outils) et Recommend (profil de modèle, contrat) |
| `contract.py` | Contrat signé HMAC-SHA256, durée de vie 5 min, vérification à la frontière d'exécution |
| `evaluation.py` | Harnais d'évaluation et seuils officiels (`evals/scout/`) |

Lancer l'évaluation : `python -m scripts.run_scout_evals`.

Spécification et seuils : dépôt [Meterless/Meterless](https://github.com/Meterless/Meterless), dossier `engines/scout-intent/` (licence Apache-2.0, © 2026 Meterless). Le jeu `evals/scout/regression_v1/injection_meterless_v1.jsonl` est repris tel quel de ce dépôt.

Écarts assumés par rapport à la spécification : pas de Stage 2 (modèle d'embeddings local), pas de plan multi-intentions, pas de `replan`. La limite de débit est appliquée par la route `/api/chat`.
