# Kwatsur — dossier de soumission (Open Agent Hackathon 2026)

Clôture **ferme** : **27 octobre 2026, 23h45 UTC**, sur HackOS. Rien ne peut être ajouté ou modifié après.

Ce dossier contient tout ce que demande la page « Exigences de soumission » (captures d'écran dans le dossier parent). Version anglaise : [`../en/`](../en/README.md).

| Élément demandé | Fichier | État |
| --- | --- | --- |
| Formulaire : nom, description, équipe, piste, composants préexistants | [`01_formulaire_soumission.md`](./01_formulaire_soumission.md) | Prêt (relire les noms puis recopier dans HackOS) |
| Explication des technologies sponsors (10 points) | [`02_explication_technologies_sponsors.md`](./02_explication_technologies_sponsors.md) | Prêt |
| Vidéo de démonstration, 1 à 4 min (15 points) | [`03_script_video_demo.md`](./03_script_video_demo.md) | **Script prêt, vidéo à enregistrer** |
| Présentation PowerPoint | [`04_presentation_kwatsur.pptx`](./04_presentation_kwatsur.pptx) | Prêt (à relire) |
| Exemples d'entrées et de sorties, traces, modèle utilisé (recommandé) | [`05_exemples_entrees_sorties.md`](./05_exemples_entrees_sorties.md) | Prêt (sorties réelles du 27/10/2026) |
| Dépôt GitHub public avec README (installation, usage, dépendances) | [`06_conformite_depot_github.md`](./06_conformite_depot_github.md) | Vérifier la branche publique livrée et y publier les modifications locales |

## À faire avant 23h45 UTC

1. Enregistrer la vidéo en suivant `03_script_video_demo.md` (3 min 45), en anglais ou en français. Ne montrer **aucune clé** : pas le fichier `.env`, pas la Console de Nightshift.
2. Vérifier la branche présentée aux juges et y publier les modifications locales ; aucune fusion ni publication n'est effectuée par cette mise à jour documentaire.
3. Sur HackOS : créer la soumission, choisir **une seule piste**, recopier `01_formulaire_soumission.md`, joindre la vidéo, le PowerPoint, le lien GitHub et le texte de `02_explication_technologies_sponsors.md`.
4. Vérifier que les deux membres de l'équipe sont bien inscrits : l'équipe est verrouillée dès la première soumission.

## Ce qui a été vérifié pour ce dossier (27/10/2026)

- Dernière suite hors réseau : **214 tests réussis, 2 ignorés**.
- Évaluation de Meterless Scout Intent : tous les seuils officiels respectés (`python -m scripts.run_scout_evals`).
- Traces historiques avec Zetaris (local, 2.4.3), Meterless Nightshift et NVIDIA Nemotron 3 Ultra : recherche, affinage, comparaison et questions. Vérifications récentes : image Cloudflare réelle, proposition persistée en attente puis refusée via l'API admin ; approbation et photos couvertes hors réseau. L'état récent de Zetaris est distingué ci-dessous.
- Mode de repli `SAMPLE_MODE=true` : fonctionne sans Zetaris, Nightshift ni Cloudflare.

## Mise à jour du produit

- Recherche fractionnée conservée ; routage simplifié par défaut (`SCOUT_ROUTING_ENABLED=false`), avec demandes explicites d'images et dépôt accessibles.
- Résultats et comparaison sous le chat dans un panneau repliable, fermé par défaut.
- Images uniquement sur demande, ciblage par nom/quartier ou rang, clarification si ambiguïté ; contexte camerounais réservé dans le prompt Cloudflare (2048 caractères), sans prétendre reconstituer le logement.
- Modération : `draft → pending → approved/rejected`, notes, dates, filtres et déconnexion admin. Vérification réelle récente : dépôt en attente dans PostgreSQL puis refus ; approbation et photos couvertes hors réseau.
- Les exemples anciens restent des traces datées. Lors des dernières vérifications, Zetaris était en erreur et le repli PostgreSQL était annoncé ; ne pas présenter une intégration comme disponible sans contrôle live.
- Les captures de présentation sont anonymisées. Après reconstruction du frontend, recharger sans cache ; ne jamais afficher le jeton ou les contacts personnels.
