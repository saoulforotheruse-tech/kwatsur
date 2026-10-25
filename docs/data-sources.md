# Sources de données

## Source actuelle : jeu de démonstration fictif

- Fichier : `db/seed/seed_demo.py`, 20 annonces à Douala et Yaoundé.
- Source enregistrée : « Données fictives Kwatsur », avec `is_demo = true`. Chaque description commence par `[DÉMO — annonce fictive]`.
- Aucune coordonnée, aucun lien et aucune disponibilité n'est inventé : `contact_information` et `source_url` restent vides, et `listing_status` vaut `unconfirmed`.
- Des informations sont volontairement inconnues (eau, électricité, mobilier, date) pour montrer qu'elles sont signalées et jamais devinées.
- Une annonce a un loyer anormalement bas, pour illustrer le signal « à vérifier ».

Ces données ne doivent pas être présentées comme un inventaire réel.

## Provenance affichée

Chaque résultat indique `source_name`, `source_is_demo`, `source_url` (si connue), `listing_status`, `verification_status` et `last_seen_at`. L'interface distingue :
- **annonce collectée** : présente dans la source ;
- **disponibilité confirmée** : jamais affirmée sans preuve, l'affichage par défaut est « Disponibilité à confirmer » ;
- **vérification** : `verification_status` reste `unverified` tant qu'aucun processus de vérification n'existe.

## Ajouter une source réelle

1. Vérifier les conditions d'utilisation : pas de scraping contraire aux conditions d'un site, pas de contournement de protection, pas de données privées.
2. Créer une `PropertySource` (`source_type`, `terms_url`, `is_demo = false`).
3. Importer les annonces avec leur identifiant d'origine (`source_property_id`, unique par source), leur URL et leur date d'observation.
4. Ou bien exposer la source dans Zetaris avec les colonnes de `LISTING_COLUMNS` (`app/integrations/data/zetaris.py`).
5. Pour une API partenaire, créer une nouvelle `ListingSource` dans `app/integrations/data/` : le reste du système n'a pas à changer.

## Données personnelles

Kwatsur ne crée pas de compte et ne stocke que les messages de la conversation et les critères. Les journaux n'enregistrent pas le contenu des messages. Les coordonnées d'une annonce ne sont affichées que si la source les fournit.
