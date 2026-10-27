"""Étape Interpret : lier les paramètres de l'intention et décider s'il faut clarifier.

Les quatre déclencheurs de clarification de la spécification :
1. top-1 dans la bande Low ; 2. top-1 et top-2 à moins de 0,05 dans la bande Medium ;
3. paramètre requis introuvable ; 4. intention à risque « high » avec une confiance < 0,95.
"""

import re
from dataclasses import dataclass, field
from typing import Literal

from app.engines.scout.registry import Intent, IntentRegistry, normalize_prompt
from app.engines.scout.sense import IntentCandidate, band_for

ClarificationTrigger = Literal["low-band", "tie", "params", "high-risk"]

TIE_WINDOW = 0.05
HIGH_RISK_PROCEED = 0.95
MAX_OPTIONS = 4
MAX_RANK = 10

ORDINAL_RANKS = {
    "premier": 1, "premiere": 1, "1er": 1, "1ere": 1,
    "deuxieme": 2, "second": 2, "seconde": 2, "2e": 2, "2eme": 2,
    "troisieme": 3, "3e": 3, "3eme": 3,
    "quatrieme": 4, "4e": 4, "4eme": 4,
    "cinquieme": 5, "5e": 5, "5eme": 5,
}
ORDINAL_PATTERN = re.compile(r"\b(" + "|".join(ORDINAL_RANKS) + r")\b")
NUMBERED_PATTERN = re.compile(
    r"\b(?:n[°o]\.?|numero|num|annonce|logement|resultat|option|le|la|et)\s*(\d{1,2})\b"
)


# Pièce demandée → valeur de `room` (ordre important : « salle de bain » avant « chambre »).
ROOM_PATTERNS = (
    ("salle_de_bain", re.compile(r"\b(salle de bains?|douche|toilettes?|wc)\b")),
    ("cuisine", re.compile(r"\bcuisine\b")),
    ("salon", re.compile(r"\b(salon|salle de sejour|sejour)\b")),
    ("chambre", re.compile(r"\bchambres?\b")),
    ("facade", re.compile(r"\b(facade|exterieur|dehors|de l.exterieur|toit|maison vue)\b")),
)


def bind_room(prompt: str) -> str:
    """Pièce citée dans le message ; la façade par défaut (« à quoi ressemble la maison ? »)."""
    text = normalize_prompt(prompt)
    for room, pattern in ROOM_PATTERNS:
        if pattern.search(text):
            return room
    return "facade"


@dataclass(frozen=True)
class Clarification:
    trigger: ClarificationTrigger
    question: str
    options: list[str]


@dataclass(frozen=True)
class Interpretation:
    intent: Intent
    confidence: float
    band: str
    parameters: dict = field(default_factory=dict)
    alternates: list[IntentCandidate] = field(default_factory=list)
    clarification: Clarification | None = None


def bind_ranks(prompt: str) -> list[int]:
    """Rangs cités dans le message (« le premier », « n°2 », « le 1 et le 3 »), dans l'ordre."""
    text = normalize_prompt(prompt)
    found: list[tuple[int, int]] = [
        (match.start(), ORDINAL_RANKS[match.group(1)]) for match in ORDINAL_PATTERN.finditer(text)
    ]
    found += [(match.start(), int(match.group(1))) for match in NUMBERED_PATTERN.finditer(text)]
    ranks: list[int] = []
    for _position, rank in sorted(found):
        if 1 <= rank <= MAX_RANK and rank not in ranks:
            ranks.append(rank)
    return ranks


def _options(registry: IntentRegistry, candidates: list[IntentCandidate]) -> list[str]:
    return [registry.get(candidate.intent_id).label for candidate in candidates[:MAX_OPTIONS]]


def interpret(
    registry: IntentRegistry,
    prompt: str,
    candidates: list[IntentCandidate],
    has_active_search: bool,
) -> Interpretation:
    if not candidates:
        # Bande Reject : repli sur l'intention sûre GENERAL, jamais sur une intention risquée.
        general = registry.get("general.help")
        return Interpretation(intent=general, confidence=0.0, band="reject")

    top = candidates[0]
    intent = registry.get(top.intent_id)
    band = band_for(top.score)
    alternates = candidates[1:]

    if band == "reject":
        return Interpretation(
            intent=registry.get("general.help"), confidence=top.score, band=band, alternates=candidates
        )

    parameters: dict = {}
    if intent.id == "contact.draft":
        ranks = bind_ranks(prompt)
        if ranks:
            parameters["rank"] = ranks[0]
    elif intent.id == "housing.compare":
        # Choix d'implémentation : sans rang cité, on compare les trois premiers résultats.
        parameters["ranks"] = (bind_ranks(prompt) or [1, 2, 3])[:3]
    elif intent.id == "listing.visualize":
        # Sans rang cité, il s'agit du premier résultat ; la réponse le précise.
        parameters["rank"] = (bind_ranks(prompt) or [1])[0]
        parameters["room"] = bind_room(prompt)

    clarification = None
    if band == "low":
        clarification = Clarification(
            "low-band",
            "Je ne suis pas sûr de comprendre. Que souhaitez-vous faire ?",
            _options(registry, candidates),
        )
    elif band == "medium" and alternates and top.score - alternates[0].score < TIE_WINDOW:
        clarification = Clarification(
            "tie", "Votre demande peut se comprendre de deux façons. Que souhaitez-vous faire ?",
            _options(registry, candidates[:2]),
        )
    elif intent.requires_active_search and not has_active_search:
        clarification = Clarification(
            "params",
            "Je n'ai pas encore de résultats à utiliser. Décrivez d'abord le logement recherché "
            "(ville, budget, nombre de chambres…).",
            [registry.get("housing.search").label],
        )
    elif any(name not in parameters for name in intent.required_parameters):
        clarification = Clarification(
            "params",
            "De quel logement parlez-vous ? Indiquez son rang dans la liste (par exemple « le n°2 »).",
            [],
        )
    elif intent.risk_class == "high" and top.score < HIGH_RISK_PROCEED:
        clarification = Clarification(
            "high-risk", "Cette action est sensible. Pouvez-vous préciser ce que vous voulez faire ?",
            _options(registry, candidates),
        )

    return Interpretation(
        intent=intent,
        confidence=top.score,
        band=band,
        parameters=parameters,
        alternates=alternates,
        clarification=clarification,
    )
