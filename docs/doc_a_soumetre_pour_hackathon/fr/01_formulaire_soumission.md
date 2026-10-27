# Formulaire de soumission HackOS

Textes prêts à recopier dans le formulaire.

## Nom du projet

**Kwatsur**

## Description courte (une phrase)

Kwatsur est un agent conversationnel qui aide à trouver un logement à louer au Cameroun : il comprend la demande en français ou à la voix, interroge les annonces via Zetaris, classe les résultats et explique chaque recommandation sans jamais inventer d'information.

## Description complète

À Douala et à Yaoundé, chercher un logement, c'est fouiller des annonces dispersées, incomplètes et parfois périmées, avec un vrai risque d'arnaque (avance demandée avant visite). Kwatsur fait ce travail à la place de l'utilisateur.

**Pour la personne qui cherche.** Elle décrit son besoin comme à un ami (« un deux-chambres à Douala vers Bonamoussadi, 150 000 FCFA max, avec eau et électricité »), au clavier ou à la voix. L'agent :
- extrait les critères avec NVIDIA Nemotron ;
- interroge les annonces via **Zetaris** ;
- applique les critères obligatoires et classe les résultats par un code déterministe, avec des raisons, des compromis et des points à vérifier ;
- signale les risques potentiels (loyer anormalement bas, annonce ancienne) ;
- fait expliquer le tout par Nemotron, sur la base des seuls faits calculés.

Elle peut affiner (« finalement 110 000 max »), comparer (« compare le premier et le deuxième »), poser une question sur une annonce, préparer un message au propriétaire, ou voir une pièce (« montre-moi la douche du n°2 »). Dans ce dernier cas, Kwatsur distingue photo propriétaire, photo d'exemple créditée et illustration IA clairement étiquetée.

**Pour le propriétaire.** Il décrit son logement dans le chat (« je loue mon studio à Bastos… »). L'agent lui demande ce qui manque, accepte ses photos, puis envoie l'annonce à un administrateur, qui la valide avant toute publication.

**Interface centrée sur la conversation.** Les annonces et la comparaison sont regroupées dans un panneau repliable, fermé par défaut, dont le compteur reste visible. Une recherche peut être décrite en plusieurs messages sans perdre les critères déjà retenus.

**Images uniquement sur demande.** Une recherche ordinaire n'envoie aucune image dans le chat. Une demande nommant Logpom cible ce logement, pas automatiquement le premier résultat ; en cas d'ambiguïté, l'agent demande de préciser. Photo du propriétaire, photo d'exemple créditée et illustration IA restent distinguées. Le prompt Cloudflare réserve une place au contexte urbain camerounais, dans la limite de 2048 caractères, sans garantir l'apparence réelle du logement. Une illustration existante est réutilisée sans nouvelle génération ; la limite quotidienne est globale à l'application.

**Modération persistante.** Les propositions confirmées sont enregistrées dans `listing_submissions` au statut `pending`, sans annonce publiée. Sur `/admin.html`, l'administrateur consulte les détails et photos, approuve ou refuse avec une note, puis retrouve les décisions dans les filtres dédiés. L'approbation crée l'annonce dans `properties` et y rattache les photos ; elle ne certifie ni le propriétaire ni la disponibilité. Le panneau est protégé par `ADMIN_TOKEN`, avec déconnexion.

**Avant les actions outillées**, le moteur **Meterless Scout Intent** :
- reconnaît l'intention ;
- bloque les injections de prompt et toute demande de paiement ;
- signe un contrat d'exécution que chaque outil vérifie.

Par défaut, `SCOUT_ROUTING_ENABLED=false` évite de classifier les fragments d'une recherche : les politesses seules reçoivent une réponse fixe, les demandes explicites d'images et de dépôt restent accessibles avec garde et contrat. Les commandes de comparaison et de contact dans le chat nécessitent `true` ; leurs boutons dans les cartes restent disponibles.

Le modèle est servi par **Meterless Nightshift** (fournisseur IA principal), avec **NVIDIA Nemotron 3 Ultra** épinglé.

Règle de conception : *l'IA comprend et explique, le code décide*. Une information inconnue reste « non renseignée », jamais devinée.

## Équipe

| Membre | GitHub |
| ---    | ---    |
| Raoul DARIL Tankam Soh | saoulforotheruse-tech |
| NOUBISSI mEIKEM Indira Leslie | ravenger26 |

Nom de l'équipe sur HackOS : **Kwatsur** (2 membres).

## Piste (une seule)

Recommandation : **The Agent That Can Explain Why**. Kwatsur produit des recommandations fondées sur des preuves :
- chaque annonce proposée vient avec ses raisons, ses compromis, ses points à vérifier et ses signaux de risque, calculés à partir des données ;
- l'explication est rédigée par Nemotron sur la base de ces seuls faits ;
- quand une information manque, l'agent le dit.

Alternative : *Solving Fragmented Intelligence* (annonces dispersées réunies derrière Zetaris).

## Composants préexistants (déclaration)

- Aucun code antérieur à l'ouverture de la fenêtre de développement (22/10/2026). Premier commit du dépôt : 23/10/2026.
- Bibliothèques open source : FastAPI, SQLAlchemy, Alembic, Pydantic, httpx, pytest, nginx, PostgreSQL.
- Spécification et seuils d'évaluation de Meterless Scout Intent, ainsi que son jeu d'injections : dépôt public Meterless (Apache-2.0). L'implémentation Python est la nôtre.
- 4 photos d'exemple de Wikimedia Commons (CC BY-SA, crédits affichés) et 20 annonces **fictives** pour la démonstration.
