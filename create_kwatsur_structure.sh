#!/usr/bin/env bash
set -Eeuo pipefail

# Crée l'arborescence Kwatsur sans écraser les fichiers existants.
# Usage :
#   chmod +x create_kwatsur_structure.sh
#   ./create_kwatsur_structure.sh [chemin-cible]
#
# Exemple :
#   ./create_kwatsur_structure.sh ./kwatsur

TARGET="${1:-./kwatsur}"

if [[ -e "$TARGET" && ! -d "$TARGET" ]]; then
  echo "Erreur : '$TARGET' existe mais n'est pas un dossier." >&2
  exit 1
fi

mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"

create_dir() {
  mkdir -p "$TARGET/$1"
}

write_if_missing() {
  local relative_path="$1"
  local content="$2"
  local full_path="$TARGET/$relative_path"

  mkdir -p "$(dirname "$full_path")"
  if [[ -e "$full_path" ]]; then
    echo "Conservé (existe déjà) : $relative_path"
  else
    printf '%s' "$content" > "$full_path"
    echo "Créé : $relative_path"
  fi
}

# Dossiers
for dir in \
  app/core app/api/routes app/schemas app/models app/repositories app/services app/jobs \
  app/integrations/llm app/integrations/data app/integrations/agent_runtime \
  app/db frontend/css frontend/js migrations/versions \
  tests/unit tests/integration tests/e2e scripts docs
do
  create_dir "$dir"
done

# Fichiers de départ (vides ou avec un court en-tête).
write_if_missing "app/main.py" '"""Point d’entrée de l’application FastAPI."""'$'\n'
write_if_missing "app/core/config.py" '"""Chargement et validation de la configuration."""'$'\n'
write_if_missing "app/core/logging.py" '"""Configuration centralisée des journaux."""'$'\n'
write_if_missing "app/core/exceptions.py" '"""Exceptions applicatives et gestion des erreurs."""'$'\n'
write_if_missing "app/api/dependencies.py" '"""Dépendances FastAPI et injection des services."""'$'\n'
write_if_missing "app/api/routes/chat.py" '"""Routes HTTP pour les conversations."""'$'\n'
write_if_missing "app/api/routes/properties.py" '"""Routes HTTP de recherche des logements."""'$'\n'
write_if_missing "app/api/routes/health.py" '"""Route de contrôle de santé."""'$'\n'
write_if_missing "app/schemas/chat.py" '"""Schémas Pydantic des conversations."""'$'\n'
write_if_missing "app/schemas/property.py" '"""Schémas Pydantic des logements."""'$'\n'
write_if_missing "app/models/property.py" '"""Modèle SQLAlchemy du logement."""'$'\n'
write_if_missing "app/models/conversation.py" '"""Modèle SQLAlchemy de conversation."""'$'\n'
write_if_missing "app/models/message.py" '"""Modèle SQLAlchemy de message."""'$'\n'
write_if_missing "app/repositories/property_repository.py" '"""Accès aux données des logements."""'$'\n'
write_if_missing "app/repositories/conversation_repository.py" '"""Accès aux conversations persistées."""'$'\n'
write_if_missing "app/services/agent_service.py" '"""Orchestration de l’agent."""'$'\n'
write_if_missing "app/services/search_service.py" '"""Recherche et filtrage des logements."""'$'\n'
write_if_missing "app/services/ranking_service.py" '"""Classement explicable des résultats."""'$'\n'
write_if_missing "app/services/conversation_service.py" '"""Gestion des conversations."""'$'\n'
write_if_missing "app/jobs/__init__.py" '"""Tâches planifiées ou exécutées en arrière-plan."""'$'\n'
write_if_missing "app/integrations/llm/base.py" '"""Contrat commun des fournisseurs IA."""'$'\n'
write_if_missing "app/integrations/llm/nemotron.py" '"""Adaptateur Nemotron à implémenter selon la documentation."""'$'\n'
write_if_missing "app/integrations/data/zetaris.py" '"""Adaptateur Zetaris à implémenter selon les accès réels."""'$'\n'
write_if_missing "app/integrations/agent_runtime/meterless.py" '"""Adaptateur Meterless à implémenter selon les outils disponibles."""'$'\n'
write_if_missing "app/db/session.py" '"""Configuration des sessions SQLAlchemy."""'$'\n'
write_if_missing "app/db/base.py" '"""Base déclarative SQLAlchemy."""'$'\n'
write_if_missing "frontend/index.html" '<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kwatsur</title>
  <link rel="stylesheet" href="/css/styles.css">
</head>
<body>
  <main id="app">
    <h1>Kwatsur</h1>
    <p>Structure initiale — interface à développer.</p>
  </main>
  <script type="module" src="/js/app.js"></script>
</body>
</html>
'
write_if_missing "frontend/css/styles.css" '/* Styles de l’interface Kwatsur — à développer. */'$'\n'
write_if_missing "frontend/js/app.js" '// Point d’entrée JavaScript du frontend.'$'\n'
write_if_missing "frontend/js/chat.js" '// Gestion de l’interface de conversation.'$'\n'
write_if_missing "frontend/js/property_cards.js" '// Affichage des cartes de logements.'$'\n'
write_if_missing "requirements.txt" '# Dépendances Python à définir après validation des versions.'$'\n'
write_if_missing ".env.example" '# Exemple sans secrets réels.
DATABASE_URL=postgresql+psycopg://postgres:change_me@db:5432/kwatsur
NEMOTRON_BASE_URL=
NEMOTRON_API_KEY=
ZETARIS_BASE_URL=
ZETARIS_API_KEY=
'
write_if_missing ".gitignore" '.env
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/
.DS_Store
'
write_if_missing "Dockerfile" '# Dockerfile à compléter après définition des dépendances applicatives.'$'\n'
write_if_missing "docker-compose.yml" '# Compose à compléter après validation de la configuration.'$'\n'
write_if_missing "alembic.ini" '# Configuration Alembic à compléter.'$'\n'

write_if_missing "README.md" '# Kwatsur — architecture

Kwatsur est un agent conversationnel de recherche et de comparaison de logements à louer, conçu d’abord pour le marché camerounais.

L’architecture s’inspire de l’organisation de `tree.txt`, en l’adaptant au domaine immobilier de Kwatsur. `architecture.tree` présente la structure cible. Cette arborescence ne signifie pas que tous les modules sont déjà implémentés.

## Architecture

Le flux principal est :

`frontend/` → `app/api/routes/` → `app/services/` → `app/repositories/` et `app/integrations/`

- `app/api/` expose l’API HTTP FastAPI. Les routes valident et traduisent les requêtes, puis délèguent aux services.
- `app/services/` porte les cas d’utilisation et les règles métier. Cette couche ne dépend ni de FastAPI ni des détails de stockage.
- `app/repositories/` encapsule l’accès aux données persistées. Les modèles SQLAlchemy restent dans `app/models/`.
- `app/integrations/` isole les fournisseurs externes derrière des adaptateurs.
- `app/jobs/` accueille les tâches planifiées ou exécutées en arrière-plan. Un job délègue le travail métier aux services.
- `app/schemas/` définit les contrats d’entrée et de sortie Pydantic ; `app/core/` et `app/db/` regroupent les fondations partagées.
- `migrations/` conserve l’historique Alembic. `frontend/` contient l’interface, et `tests/` les tests unitaires, d’intégration et E2E.

Les dépendances vont vers les contrats et la logique métier, pas depuis les services vers les détails HTTP ou les SDK fournisseurs. Les dépendances concrètes sont assemblées dans l’API ou au démarrage de l’application.

## Documentation des dossiers

Chaque répertoire de code contient un fichier `<nom_du_dossier>_readme.md` décrivant son rôle et ses règles de contribution. Ces notes sont indépendantes afin que la responsabilité d’un répertoire soit compréhensible sans devoir lire toute la documentation du projet. Le script `create_kwatsur_structure.sh` crée les notes manquantes sans remplacer celles déjà présentes.

## Règles

- Garder chaque module dans sa couche et déléguer plutôt que dupliquer la logique métier.
- Ne pas inventer de données, d’endpoints ou d’intégrations.
- Marquer les données de démonstration comme fictives.
- Garder les secrets dans `.env`, jamais dans Git ni dans le frontend.
- Ajouter ou adapter les tests lors d’un changement de comportement.
- Ne déclarer un test réussi qu’après l’avoir exécuté.

## Structure

Consulte `architecture.tree` pour la vue arborescente et `create_kwatsur_structure.sh` pour générer le squelette dans un dossier cible. Le script conserve les fichiers existants.
'

write_if_missing "architecture.tree" 'Kwatsur/
├── app/
│   ├── api/
│   │   └── routes/
│   ├── core/
│   ├── db/
│   ├── integrations/
│   │   ├── agent_runtime/
│   │   ├── data/
│   │   └── llm/
│   ├── jobs/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   └── services/
├── docs/
├── frontend/
│   ├── css/
│   └── js/
├── migrations/
│   └── versions/
├── scripts/
└── tests/
    ├── e2e/
    ├── integration/
    └── unit/
'

# README in every directory; do not overwrite existing docs.
declare -A DIR_DOCS
DIR_DOCS["app"]="Code backend Python. Garde ici les modules applicatifs et sépare API, logique métier, persistance et intégrations."
DIR_DOCS["app/core"]="Configuration, journaux et exceptions partagés. Ne place pas ici la logique métier de recherche."
DIR_DOCS["app/api"]="Couche HTTP FastAPI. Les routes valident les requêtes et appellent les services ; elles ne portent pas la logique métier complète."
DIR_DOCS["app/api/routes"]="Contrôleurs HTTP par domaine. Retourne des réponses HTTP cohérentes et délègue les opérations aux services."
DIR_DOCS["app/schemas"]="Contrats Pydantic pour valider les entrées et sorties. À distinguer des modèles SQLAlchemy."
DIR_DOCS["app/models"]="Entités SQLAlchemy et relations de persistance. Pas d’appels réseau ni d’orchestration dans les modèles."
DIR_DOCS["app/repositories"]="Centralise les lectures et écritures en base. Évite les requêtes SQL dispersées dans les routes et services."
DIR_DOCS["app/services"]="Cas d’utilisation et logique métier : recherche, classement, conversations et orchestration de l’agent."
DIR_DOCS["app/jobs"]="Tâches planifiées ou exécutées en arrière-plan. Les jobs coordonnent les services et ne dupliquent pas les règles métier."
DIR_DOCS["app/integrations"]="Adaptateurs des services externes. Respecte les documentations officielles et n’invente aucune API."
DIR_DOCS["app/integrations/llm"]="Contrats et adaptateurs des fournisseurs de langage, notamment Nemotron. Le métier dépend d’un contrat, pas d’un SDK spécifique."
DIR_DOCS["app/integrations/data"]="Adaptateurs des sources de données, dont Zetaris. Normalise les résultats et conserve la provenance."
DIR_DOCS["app/integrations/agent_runtime"]="Encapsule Meterless si son utilisation est pertinente et réellement disponible ; évite les doublons d’orchestration."
DIR_DOCS["app/db"]="Configuration SQLAlchemy, sessions et base déclarative. Les requêtes propres aux logements restent dans les repositories."
DIR_DOCS["frontend"]="Interface web. Appelle l’API backend et ne contient aucun secret ni accès direct à PostgreSQL."
DIR_DOCS["frontend/css"]="Styles, mise en page responsive et états visuels. Pas de logique métier."
DIR_DOCS["frontend/js"]="Modules JavaScript de l’interface et appels HTTP. Les règles métier restent côté serveur."
DIR_DOCS["migrations"]="Historique des changements de schéma géré par Alembic. Versionne les évolutions de base."
DIR_DOCS["migrations/versions"]="Fichiers de migration versionnés. Vérifie les fonctions upgrade et downgrade."
DIR_DOCS["tests"]="Tous les tests automatisés. Les tests doivent être reproductibles et documenter leurs prérequis."
DIR_DOCS["tests/unit"]="Tests isolés des règles métier avec dépendances simulées."
DIR_DOCS["tests/integration"]="Tests des interactions entre composants et base de test. Les appels externes doivent être explicitement configurés."
DIR_DOCS["tests/e2e"]="Scénarios complets du parcours utilisateur, documentés et reproductibles."
DIR_DOCS["scripts"]="Scripts répétables d’initialisation, maintenance ou démonstration. Évite les actions destructrices non confirmées."
DIR_DOCS["docs"]="Décisions d’architecture, diagrammes et procédures techniques. Maintiens la documentation alignée sur le code."
DIR_DOCS["migrations/versions"]="Fichiers de migration versionnés. Vérifie les fonctions upgrade et downgrade."

for dir in "${!DIR_DOCS[@]}"; do
  folder_name="$(basename "$dir")"
  content="# ${folder_name} — rôle du dossier

${DIR_DOCS[$dir]}

## Règles de contribution

- Garde ce dossier centré sur sa responsabilité.
- Utilise des noms explicites et des interfaces simples.
- Ajoute ou adapte les tests lorsque le comportement change.
- Mets à jour cette documentation si le rôle du dossier évolue.
"
  write_if_missing "$dir/${folder_name}_readme.md" "$content"
done

# Add Python package markers where useful, without overwriting.
for pkg in app app/core app/api app/api/routes app/schemas app/models app/repositories app/services app/jobs app/integrations app/integrations/llm app/integrations/data app/integrations/agent_runtime app/db; do
  write_if_missing "$pkg/__init__.py" ""
done

echo
echo "Structure Kwatsur créée dans : $TARGET"
echo "Les fichiers existants ont été conservés. Consulte README.md avant de commencer le développement."
