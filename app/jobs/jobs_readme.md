# jobs — rôle du dossier

Tâches planifiées ou exécutées en arrière-plan, par exemple des traitements d’entretien ou de recalcul. Ce dossier reste vide tant qu’aucun besoin concret de tâche asynchrone n’existe.

## Règles de contribution

- Délègue les règles métier aux services au lieu de les réimplémenter dans un job.
- Garde les tâches répétables et rends explicites leurs entrées, sorties et erreurs.
- N’ajoute un ordonnanceur ou un système de file d’attente qu’après validation du besoin.
- Ajoute ou adapte les tests lorsque le comportement change.
