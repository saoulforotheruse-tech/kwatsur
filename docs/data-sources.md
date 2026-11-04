# Sources de données

## Source actuelle : jeu de démonstration fictif

- Fichier : `db/seed/seed_demo.py`, 20 annonces à Douala et Yaoundé.
- Source enregistrée : « Données fictives Kwatsur », avec `is_demo = true`. Chaque description commence par `[DÉMO — annonce fictive]`.
- Aucune coordonnée, aucun lien et aucune disponibilité n'est inventé : `contact_information` et `source_url` restent vides, et `listing_status` vaut `unconfirmed`.
- Des informations sont volontairement inconnues (eau, électricité, mobilier, date) pour montrer qu'elles sont signalées et jamais devinées.
- Une annonce a un loyer anormalement bas, pour illustrer le signal « à vérifier ».

Ces données ne doivent pas être présentées comme un inventaire réel.

## Annonces internationales : Untera

Les recherches hors des pays de `LOCAL_LISTING_COUNTRIES` (Cameroun par défaut) interrogent l'API [Untera](https://untera.io/developers) au lieu de Zetaris/PostgreSQL. Le parcours camerounais ne change pas.

- **Routage** (`app/services/search_service.py`) : le modèle IA déduit le code pays ISO du lieu cité (« Lisbonne » → `PT`, « aux États-Unis » → `US`). Aucune liste de pays n'est maintenue dans le code : un pays absent ou inconnu reste sur la source locale. Hors Cameroun, un pays suffit pour chercher (pas de question sur la ville).
- **Appel** (`app/integrations/data/untera.py`) : `GET /api/v1/listings/search` avec l'en-tête `X-API-Key`, paramètres `country`, `location`, `transaction`, `minBeds`, et `minPrice`/`maxPrice` seulement si le budget est en USD (monnaie de filtrage d'Untera). Un seul appel par recherche (`pageSize=50`). Tous les filtres obligatoires sont refaits par le backend.
- **Location ou vente** : Untera publie surtout des ventes. Si l'utilisateur demande une location et qu'il n'y en a aucune, Kwatsur le dit, puis montre les offres disponibles avec un badge « À vendre » et la mention « prix de vente » ; le budget mensuel n'est pas appliqué à ces prix. Sans préférence, ventes et locations sont mélangées, chacune étiquetée. Une annonce dont la nature n'est pas indiquée affiche « location ou vente non précisée ».
- **Monnaies** : le prix d'origine est affiché tel quel (EUR, GBP…). Aucune conversion n'est faite par Kwatsur : un budget dans une autre monnaie que l'annonce n'exclut pas l'annonce, il produit un point « à vérifier ». Seul le prix en USD fourni par Untera sert à comparer un budget en USD.
- **Données inconnues** : eau, électricité et mobilier ne sont pas fournis par Untera et restent « non renseignés ». Les terrains (`type = land`) sont écartés.
- **Photos** : celles publiées par l'annonce d'origine, affichées par leur lien (servies par `api.untera.io` ou directement par le portail d'origine, comme homes.com ; la CSP de nginx autorise les images `https:`, chargées sans référent). Si le site d'origine refuse l'affichage, la carte le dit et renvoie vers l'annonce : Kwatsur ne contourne aucune protection, avec l'étiquette « Photo de l'annonce » et un lien vers l'annonce. La première apparaît sur la carte ; une demande explicite (« montre-moi des photos du n°2 », « show me pictures of the house ») en affiche jusqu'à 4 dans la conversation. Untera ne classe pas les photos par pièce : la réponse le dit si une pièce précise est demandée. Aucune illustration IA n'est générée pour une annonce internationale.
- **Attribution** : l'offre gratuite exige une mention visible « Powered by Untera » avec un lien vers untera.io ; elle est affichée sur chaque carte et dans les avis de la réponse.
- **Identifiants** : texte (`redfin_com_…`), contrairement aux entiers des annonces locales. `GET /api/properties/{id}` interroge Untera pour un identifiant texte.
- **Sans clé** : la réponse l'indique (« UNTERA_API_KEY manquante ») et ne renvoie aucune annonce ; elle ne se rabat pas sur la base camerounaise.
- **Test réel** : `GET /api/integrations/status?live=true` lance une recherche Untera d'une annonce au Portugal.

Limites connues : la documentation d'Untera ne détaille ni le schéma complet d'une annonce, ni les valeurs admises de `transaction` et `type`. Les noms de champs sont lus sous leurs deux formes observées (exemples de la documentation en snake_case, site untera.io en camelCase) ; `transaction` vaut `sale` ou `rent_monthly` dans les réponses observées, et le paramètre `transaction=rent|sale` vient des pages du site. Le filtre `location` semble peu fiable chez Untera (« New York » renvoie des annonces d'autres États) : une adresse qui ne cite pas la ville demandée est signalée en compromis et classée après les autres. Le mode démo sans IA (`LLM_PROVIDER=rules`) ne reconnaît pas les pays : seul le modèle IA route vers Untera.

## Photos d'exemple

`db/seed/sample_photos.json` liste 4 photos de logements au Cameroun issues de Wikimedia Commons (CC BY-SA 4.0), rattachées à des annonces fictives : Denver, Biyem-Assi, Akwa et Emana. Elles ne montrent pas ces logements. Elles sont étiquetées « Photo d'exemple » avec auteur, licence et lien, comme l'exige la licence. Chargement : `python -m scripts.seed_sample_photos`.

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
