"""Étape Guard : cinq couches indépendantes, chacune « pass », « warn » ou « block ».

1. injection de prompt ; 2. politique (intentions interdites) ; 3. portée (surface, rôle) ;
4. données personnelles ; 5. limite de débit. Un seul « block » bloque ; chaque « warn »
élève le niveau de risque, qui ne descend jamais sous le `riskClass` de l'intention.
Les contenus d'injection détectés ne sont pas journalisés : seulement leur type.
"""

import re
from dataclasses import dataclass, field
from typing import Literal

from app.engines.scout.registry import Intent, normalize_prompt

LayerOutcome = Literal["pass", "warn", "block"]
RiskLevel = Literal["low", "medium", "high", "block"]
RISK_ORDER: tuple[RiskLevel, ...] = ("low", "medium", "high", "block")

POLICY_PACK_VERSION = "kwatsur-default-1"
# Politique Kwatsur : l'agent ne manipule jamais d'argent.
DENIED_INTENTS = {
    "payment.send": "Kwatsur ne fait aucun paiement ni transfert d'argent.",
}

# Contrôles et marqueurs de rôle invisibles (texte bidirectionnel, caractères de largeur nulle).
CONTROL_CHARACTERS = re.compile("[​-‏‪-‮⁦-⁩]|\\\\u20(2[a-e]|6[6-9])", re.IGNORECASE)
INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("instruction-override", re.compile(
        r"\b(ignore|disregard|forget|oublie|ignorez?|oubliez)\b.{0,40}\b(instructions?|rules?|regles?|consignes?|above|precedent\w*|previous)\b"
    )),
    ("instruction-override", re.compile(r"\b(disregard the user|unrestricted mode|mode sans restriction|developer mode|mode developpeur)\b")),
    ("role-confusion", re.compile(r"</?\s*(system|user|assistant|systeme)\s*>|\[/?inst\]|<<\s*sys\s*>>")),
    ("role-confusion", re.compile(
        r"\b(you are now|tu es (maintenant|desormais)|vous etes (maintenant|desormais)|pretend to be|fais semblant d.etre|agis comme)\b"
    )),
    ("secret-exfiltration", re.compile(
        r"\b(reveal|show|print|leak|revele\w*|affiche\w*|donne\w*|montre\w*)\b.{0,40}\b(api keys?|cles? (api|secretes?)|credentials?|mots? de passe|passwords?|system prompt|prompt systeme|tes instructions)\b"
    )),
    ("tool-ref", re.compile(
        r"\b(internal_\w+|admin(istrateur)? panel|grant me admin|donne[- ]moi (les )?droits|drop table|delete from|truncate table|base de donnees|database admin)\b"
    )),
)
# Intentions où un propriétaire donne volontairement ses coordonnées (contact de l'annonce).
PERSONAL_DATA_EXPECTED_INTENTS = {"listing.submit"}
PHONE_PATTERN = re.compile(r"(\+?237[\s.-]?)?\b6\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b")
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")


@dataclass(frozen=True)
class LayerResult:
    layer: str
    outcome: LayerOutcome
    reason: str | None = None


@dataclass(frozen=True)
class GuardResult:
    level: RiskLevel
    flags: list[dict] = field(default_factory=list)
    redactions: list[dict] = field(default_factory=list)
    reason: str | None = None
    layers: list[LayerResult] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.level == "block"


def detect_injection(prompt: str) -> list[str]:
    """Types d'injection détectés (liste vide si le message est sain)."""
    kinds = ["control-bytes"] if CONTROL_CHARACTERS.search(prompt) else []
    text = normalize_prompt(prompt)
    for kind, pattern in INJECTION_PATTERNS:
        if pattern.search(text) and kind not in kinds:
            kinds.append(kind)
    return kinds


def _escalate(level: RiskLevel) -> RiskLevel:
    return RISK_ORDER[min(RISK_ORDER.index(level) + 1, len(RISK_ORDER) - 2)]


def run_guard(
    prompt: str,
    intent: Intent,
    surface: str,
    role: str,
    competing_intents: tuple[str, ...] = (),
) -> GuardResult:
    """`competing_intents` : autres candidats au-dessus de la bande Low. Une action interdite
    parmi eux bloque aussi, pour ne jamais « deviner » une intention sûre à sa place."""
    layers: list[LayerResult] = []
    flags: list[dict] = []
    redactions: list[dict] = []

    injection_kinds = detect_injection(prompt)
    if injection_kinds:
        layers.append(LayerResult("injection", "block", "Instruction suspecte détectée dans le message."))
        flags += [{"kind": "injection", "detail": kind} for kind in injection_kinds]
    else:
        layers.append(LayerResult("injection", "pass"))

    denial = next(
        (DENIED_INTENTS[intent_id] for intent_id in (intent.id, *competing_intents) if intent_id in DENIED_INTENTS),
        None,
    )
    layers.append(LayerResult("policy", "block", denial) if denial else LayerResult("policy", "pass"))

    if surface not in intent.surfaces or role not in intent.roles:
        layers.append(LayerResult("scope", "block", "Action non autorisée sur cette interface."))
    else:
        layers.append(LayerResult("scope", "pass"))

    found = [("phone", PHONE_PATTERN), ("email", EMAIL_PATTERN)]
    detected = [kind for kind, pattern in found if pattern.search(prompt)]
    if detected and intent.id in PERSONAL_DATA_EXPECTED_INTENTS:
        layers.append(LayerResult("sensitivity", "pass", "Coordonnées attendues pour une annonce."))
    elif detected:
        layers.append(LayerResult("sensitivity", "warn", "Coordonnées personnelles dans le message."))
        redactions += [{"dataClass": kind, "action": "not-forwarded-to-tools"} for kind in detected]
    else:
        layers.append(LayerResult("sensitivity", "pass"))

    # La limite de débit est appliquée avant Scout, par la route /api/chat (SlidingWindowRateLimiter).
    layers.append(LayerResult("rate-limit", "pass", "Appliquée par la route /api/chat."))

    blocking = [layer for layer in layers if layer.outcome == "block"]
    if blocking:
        return GuardResult("block", flags, redactions, blocking[0].reason, layers)

    level: RiskLevel = intent.risk_class
    for layer in layers:
        if layer.outcome == "warn":
            level = _escalate(level)
            flags.append({"kind": layer.layer, "detail": layer.reason})
    return GuardResult(level, flags, redactions, None, layers)
