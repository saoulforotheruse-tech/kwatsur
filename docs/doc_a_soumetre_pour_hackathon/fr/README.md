# Kwatsur — dossier de soumission (Open Agent Hackathon 2026)

Clôture **ferme** : **27 octobre 2026, 23h45 UTC**, sur HackOS. Rien ne peut être ajouté ou modifié après.

Ce dossier contient tout ce que demande la page « Exigences de soumission » (captures d'écran dans le dossier parent). Version anglaise : [`../en/`](../en/README.md).

| Élément demandé | Fichier | État |
| --- | --- | --- |
| Formulaire : nom, description, équipe, piste, composants préexistants | [`01_formulaire_soumission.md`](./01_formulaire_soumission.md) | Prêt (à recopier dans HackOS ; compléter le nom du 2e membre) |
| Explication des technologies sponsors (10 points) | [`02_explication_technologies_sponsors.md`](./02_explication_technologies_sponsors.md) | Prêt |
| Vidéo de démonstration, 1 à 4 min (15 points) | [`03_script_video_demo.md`](./03_script_video_demo.md) | **Script prêt, vidéo à enregistrer** |
| Présentation PowerPoint | [`04_presentation_kwatsur.pptx`](./04_presentation_kwatsur.pptx) | Prêt (à relire) |
| Exemples d'entrées et de sorties, traces, modèle utilisé (recommandé) | [`05_exemples_entrees_sorties.md`](./05_exemples_entrees_sorties.md) | Prêt (sorties réelles du 27/10/2026) |
| Dépôt GitHub public avec README (installation, usage, dépendances) | [`06_conformite_depot_github.md`](./06_conformite_depot_github.md) | Dépôt déjà public ; **fusionner `version4.0` dans `main`** |

## À faire avant 23h45 UTC

1. Enregistrer la vidéo en suivant `03_script_video_demo.md` (3 min 45), en anglais ou en français. Ne montrer **aucune clé** : pas le fichier `.env`, pas la Console de Nightshift.
2. Fusionner la branche `version4.0` dans `main` (le dépôt est déjà public).
3. Sur HackOS : créer la soumission, choisir **une seule piste**, recopier `01_formulaire_soumission.md`, joindre la vidéo, le PowerPoint, le lien GitHub et le texte de `02_explication_technologies_sponsors.md`.
4. Vérifier que les deux membres de l'équipe sont bien inscrits : l'équipe est verrouillée dès la première soumission.

## Ce qui a été vérifié pour ce dossier (27/10/2026)

- 148 tests automatiques réussis, sans réseau.
- Évaluation de Meterless Scout Intent : tous les seuils officiels respectés (`python -m scripts.run_scout_evals`).
- Parcours réels avec Zetaris (local, 2.4.3), Meterless Nightshift et NVIDIA Nemotron 3 Ultra : recherche, affinage, comparaison, question, image d'une pièce, proposition d'annonce par un propriétaire validée par l'administrateur, injection et paiement bloqués.
- Mode de repli `SAMPLE_MODE=true` : fonctionne sans Zetaris, Nightshift ni Cloudflare.
