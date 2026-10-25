# API disponible

L’API est exposée par FastAPI. La documentation interactive est accessible sur `/docs` lorsque l’application tourne.

## Vérification

`GET /health` vérifie l’application et la connexion PostgreSQL. Il renvoie `503` si la base ne répond pas.

## Logements

`GET /api/properties` recherche les annonces visibles. Tous les paramètres sont facultatifs :

| Paramètre | Rôle |
| --- | --- |
| `city` | Ville, comparée sans tenir compte de la casse |
| `neighborhood` | Quartier préféré pour l’ordre des résultats |
| `min_rent`, `max_rent` | Bornes inclusives du loyer mensuel |
| `bedrooms` | Nombre exact de chambres |
| `water_available`, `electricity_available` | Équipement requis (`true` ou `false`) |
| `furnished` | Mobilier requis (`true` ou `false`) |
| `limit` | Nombre maximal de résultats, entre 1 et 100 (20 par défaut) |

La ville, le budget, le nombre de chambres et les équipements demandés éliminent les annonces qui ne correspondent pas. Le quartier sert à privilégier les résultats proches sans écarter automatiquement les autres quartiers de la ville. Une annonce retirée n’est jamais renvoyée.

La réponse contient le total trouvé et les résultats ordonnés. Chaque résultat expose la provenance, le statut de confirmation, les raisons du classement et les données absentes. Le champ `source_is_demo` permet de distinguer les exemples fictifs.

`GET /api/properties/{property_id}` renvoie le détail d’une annonce visible. Une annonce absente ou retirée renvoie `404`.

## Pas encore disponible

Il n’existe pas encore de route de conversation IA. La recherche actuelle utilise des filtres structurés ; l’analyse du langage naturel dépend de l’intégration Nemotron et des accès officiels.
