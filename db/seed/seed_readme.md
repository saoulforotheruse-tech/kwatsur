# seed — rôle du dossier

`seed_demo.py` ajoute vingt logements camerounais fictifs pour tester les filtres et la comparaison. Il est répétable : les mêmes annonces ne sont pas ajoutées une seconde fois.

`sample_photos.json` associe des photos Wikimedia Commons aux logements de démonstration. Ces photos sont des exemples libres de droit, pas des photos des annonces ; l'interface les étiquette et affiche leur crédit.

L'appartement de Logpom (`demo-dla-logpom-01`, Douala, 2 chambres, 95 000 FCFA/mois) n'a volontairement pas de photo d'exemple dans ce manifeste : il sert à tester « Génère une image de la façade du premier à partir de sa description ». Une illustration générée est conservée et réutilisée pour cette pièce ; réexécuter le seeder ne supprime pas les images déjà en base.

## Règles de contribution

- Exécute-le après `alembic upgrade head` avec `python -m db.seed.seed_demo`.
- Exécute `python -m scripts.seed_sample_photos` pour ajouter les photos d'exemple dans `property_images` et les fichiers dans `MEDIA_DIRECTORY`.
- Ne présente jamais ces annonces comme des offres réelles ou confirmées.
- Ne présente jamais une photo d'exemple comme une photo du logement auquel elle est associée.
- N’ajoute aucune coordonnée personnelle ou donnée réelle sans autorisation.
