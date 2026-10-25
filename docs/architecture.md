# Comment fonctionne Kwatsur

Kwatsur sépare l’interface, l’API, les règles métier et la base pour qu’une modification reste localisée.

## Parcours d’une recherche

1. L’utilisateur indique sa ville, son budget, le nombre de chambres et les équipements souhaités dans `frontend/public/`.
2. `app/api/routes/properties.py` valide les paramètres et appelle le service de recherche.
3. `app/services/search_service.py` demande les annonces au repository et prépare des explications lisibles.
4. `app/repositories/property_repository.py` construit la requête SQLAlchemy : ville, budget, chambres et équipements sont des filtres stricts. Une annonce retirée n’est pas affichée.
5. PostgreSQL renvoie les annonces. Les résultats sont ordonnés par correspondance de quartier, quantité d’informations renseignées, loyer puis identifiant. Ce tri est reproductible et n’est pas un score de confiance.
6. Le navigateur affiche les annonces, leur source, les données manquantes et permet d’en comparer jusqu’à trois.

Une valeur inconnue reste `null` dans la base et apparaît comme « non renseignée » dans l’interface. Le quartier est une préférence de classement : un autre quartier de la même ville peut être montré, mais l’écart est explicité.

## Organisation

- `app/api/` : validation HTTP et dépendances FastAPI.
- `app/services/` : règles et réponses du cas d’usage.
- `app/repositories/` : requêtes persistantes.
- `app/models/` : tables SQLAlchemy.
- `app/schemas/` : contrats validés de l’API.
- `app/db/` : moteur et sessions de l’application.
- `db/migrations/` : versions Alembic du schéma.
- `db/seed/` : données de développement explicitement fictives.
- `frontend/public/` : interface accessible au navigateur.

## Données principales

`PropertySource` décrit la provenance d’une annonce et indique si la source est une démonstration. `Property` porte les informations du logement, son statut de confirmation et les valeurs qui peuvent être inconnues. `Conversation` conserve un identifiant de session et un JSON de critères ; `Message` prépare l’historique des échanges.

La migration initiale se trouve dans `db/migrations/versions/`. Une modification de modèle doit toujours être accompagnée d’une nouvelle migration. Le seed peut être rejoué sans dupliquer ses trois exemples.

## Limites actuelles

Le parcours livré recherche dans PostgreSQL et utilise des exemples fictifs. Il ne comprend pas encore une demande écrite libre, ne récupère pas de vraies annonces et n’appelle pas Nemotron, Zetaris ou Meterless. Ces services nécessitent les instructions et accès officiels du hackathon ; aucun comportement simulé ne doit être présenté comme une intégration.
