# seed — rôle du dossier

`seed_demo.py` ajoute trois logements camerounais fictifs pour tester les filtres et la comparaison. Il est répétable : les mêmes annonces ne sont pas ajoutées une seconde fois.

## Règles de contribution

- Exécute-le après `alembic upgrade head` avec `python -m db.seed.seed_demo`.
- Ne présente jamais ces annonces comme des offres réelles ou confirmées.
- N’ajoute aucune coordonnée personnelle ou donnée réelle sans autorisation.
