"""Mode démo sans IA (LLM_PROVIDER=rules) : critères extraits par des règles déterministes.

Destiné au jury et aux essais sans clé ni Nightshift. Il ne comprend que les formulations
courantes (ville, quartier après « vers / à / quartier », type, budget, chambres, eau,
électricité, meublé) et n'invente rien : ce qu'il ne reconnaît pas reste inconnu.
L'explication est alors rédigée par le gabarit du backend, choisi par Scout.
"""

import re

from app.core.exceptions import IntegrationNotConfiguredError
from app.integrations.llm.base import ChatTurn, ReplyContext
from app.schemas.chat import ReplyAuthor
from app.schemas.criteria import CANONICAL_CITIES, CriteriaExtraction, SearchCriteria, normalize_text

NUMBER_WORDS = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6}
PROPERTY_TYPES = (
    ("appartement", r"\bappart(ement)?s?\b"),
    ("studio", r"\bstudios?\b"),
    ("maison", r"\bmaisons?\b"),
    ("villa", r"\bvillas?\b"),
    ("duplex", r"\bduplex\b"),
)
KNOWN_PREFERENCES = (
    ("proche des transports", r"\bproche (des|du) (transports?|taxis?|routes?|goudron)\b"),
    ("calme", r"\bcalme\b"),
    ("parking", r"\bparking\b"),
    ("sécurisé", r"\bsecuris\w*"),
)
BEDROOMS_PATTERN = re.compile(r"\b(\d{1,2}|" + "|".join(NUMBER_WORDS) + r")[ -]?chambres?\b")
AMOUNT_PATTERN = re.compile(r"(\d{1,3}(?:[ .]\d{3})+|\d{4,7}|\d{2,3} ?(?:k|mille)\b)")
MINIMUM_WORDS = re.compile(r"\b(au moins|minimum|a partir de|plus de)\s*$")
NEIGHBORHOOD_PATTERN = re.compile(
    r"\b(?:vers|à|a|au|quartier|près de|pres de|côté|cote)\s+([A-ZÉÈ][\w'’-]+(?:[ -][A-ZÉÈ][\w'’-]+)?)"
)
NOT_NEIGHBORHOODS = {"fcfa", "xaf", "cfa"}


def _amount(text: str) -> int:
    if text.endswith(("k", "mille")):
        return int(re.sub(r"\D", "", text)) * 1000
    return int(re.sub(r"\D", "", text))


def parse_criteria(message: str, current: SearchCriteria) -> CriteriaExtraction:
    text = normalize_text(message)
    updates: dict = {}
    removed: list[str] = []

    for normalized_city, city in CANONICAL_CITIES.items():
        if re.search(rf"\b{re.escape(normalized_city)}\b", text):
            updates["city"] = city
            break

    for match in NEIGHBORHOOD_PATTERN.finditer(message):
        candidate = match.group(1).strip()
        if normalize_text(candidate) not in CANONICAL_CITIES and normalize_text(candidate) not in NOT_NEIGHBORHOODS:
            updates["neighborhood"] = candidate
            break

    for property_type, pattern in PROPERTY_TYPES:
        if re.search(pattern, text):
            updates["property_type"] = property_type
            break

    bedrooms = BEDROOMS_PATTERN.search(text)
    if bedrooms:
        value = bedrooms.group(1)
        updates["bedrooms"] = NUMBER_WORDS.get(value) or int(value)
    elif "property_type" not in updates and re.search(r"\bune chambre\b", text):
        updates["property_type"] = "chambre"

    for match in AMOUNT_PATTERN.finditer(text):
        field = "min_rent" if MINIMUM_WORDS.search(text[: match.start()]) else "max_rent"
        updates[field] = _amount(match.group(1))

    if re.search(r"\beau\b", text):
        updates["water_available"] = True
    if re.search(r"\b(electricite|courant|eneo)\b", text):
        updates["electricity_available"] = True
    if re.search(r"\bnon meubl\w*|\bpas meubl\w*|\bvide\b", text):
        updates["furnished"] = False
    elif re.search(r"\bmeubl\w*", text):
        updates["furnished"] = True

    preferences = [label for label, pattern in KNOWN_PREFERENCES if re.search(pattern, text)]
    if preferences:
        updates["preferences"] = preferences

    if re.search(r"\b(peu importe|n.importe quel)( le)? quartier\b", text):
        removed.append("neighborhood")
        updates.pop("neighborhood", None)
    if re.search(r"\b(peu importe|n.importe quel)( le)? (prix|budget|loyer)\b", text):
        removed += ["min_rent", "max_rent"]

    intent = "refine" if not current.is_empty() else "search"
    return CriteriaExtraction(intent=intent, updates=updates, remove_fields=removed)


class RuleBasedProvider:
    """Fournisseur sans IA : extraction par règles ; l'explication vient du gabarit du backend."""

    name: ReplyAuthor = "rules"

    def extract_criteria(
        self, message: str, _history: list[ChatTurn], current: SearchCriteria
    ) -> CriteriaExtraction:
        return parse_criteria(message, current)

    def write_reply(self, _context: ReplyContext) -> str:
        # Scout oriente « reply.explain » vers le gabarit quand aucun modèle n'est disponible.
        raise IntegrationNotConfiguredError("Mode démo : aucune IA n'est configurée.")
