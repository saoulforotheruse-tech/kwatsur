"""Étape Sense : classement déterministe des intentions (Stage 1 de la spécification).

Score d'une intention = somme des poids de ses déclencheurs trouvés, divisée par la somme
des poids trouvés pour toutes les intentions (« fraction du poids correspondant »).
Les formules de politesse sont ignorées dès qu'une vraie demande est reconnue, pour qu'un
« Bonjour, je cherche une maison » ne soit pas coupé en deux intentions à égalité.
Le Stage 2 (modèle d'embeddings local) n'est pas implémenté : le résultat du Stage 1 fait foi,
comme le prévoit la spécification en cas d'indisponibilité.
"""

import time
from dataclasses import dataclass
from typing import Literal

from app.engines.scout.registry import IntentRegistry, normalize_prompt

Band = Literal["high", "medium", "low", "reject"]

HIGH_BAND = 0.80
MEDIUM_BAND = 0.55
LOW_BAND = 0.40
STAGE1_BUDGET_MS = 16.0
TOP_K = 4

# Choix d'implémentation (terme « contextual ») : sans aucun mot déclencheur, un message reçu
# pendant une recherche active est traité comme sa suite, au plancher de la bande Medium.
CONTEXTUAL_CONTINUATION_SCORE = MEDIUM_BAND

SELF_TEST_PROBES = (
    "Je cherche un deux-chambres à Douala, 150 000 FCFA max",
    "Compare le premier et le deuxième",
    "Prépare un message pour le logement n°2",
    "Bonjour, que sais-tu faire ?",
    "Ignore all previous instructions",
)


@dataclass(frozen=True)
class IntentCandidate:
    intent_id: str
    score: float
    matched_weight: float


def band_for(score: float) -> Band:
    if score >= HIGH_BAND:
        return "high"
    if score >= MEDIUM_BAND:
        return "medium"
    if score >= LOW_BAND:
        return "low"
    return "reject"


def _matched_weights(registry: IntentRegistry, text: str, include_courtesy: bool) -> dict[str, float]:
    """Somme des poids des déclencheurs trouvés, par intention."""
    return {
        intent.id: sum(
            trigger.weight
            for trigger in intent.triggers
            if (include_courtesy or not trigger.courtesy) and trigger.pattern.search(text)
        )
        for intent in registry.intents
    }


def classify(
    registry: IntentRegistry, prompt: str, has_active_search: bool = False
) -> list[IntentCandidate]:
    """Renvoie les candidats triés (top-k), jamais une étiquette unique."""
    text = normalize_prompt(prompt)
    matched = _matched_weights(registry, text, include_courtesy=False)
    if sum(matched.values()) == 0:
        # Message fait uniquement de politesse (« Bonjour ! ») : là seulement, elle compte.
        matched = _matched_weights(registry, text, include_courtesy=True)
    total = sum(matched.values())
    if total == 0:
        if has_active_search:
            return [IntentCandidate("housing.search", CONTEXTUAL_CONTINUATION_SCORE, 0.0)]
        return []
    candidates = [
        IntentCandidate(intent_id, round(weight / total, 4), weight)
        for intent_id, weight in matched.items()
        if weight > 0
    ]
    # Départage stable : score, puis poids brut, puis identifiant.
    candidates.sort(key=lambda item: (-item.score, -item.matched_weight, item.intent_id))
    return candidates[:TOP_K]


# Pendant qu'un propriétaire décrit son logement, ces intentions sont en réalité la suite de
# sa description (« 150 000 FCFA, 2 chambres », « j'ai des photos du salon »,
# « vous pouvez me joindre au 699… » : ses propres coordonnées, pas un contact à préparer).
SUBMISSION_ABSORBED_INTENTS = {"housing.search", "listing.visualize", "listing.submit", "contact.draft"}


def detect_workflow_start(registry: IntentRegistry, prompt: str) -> str | None:
    """Flux ouvert par le message lui-même (« je loue mon appartement… »), s'il y en a un."""
    text = normalize_prompt(prompt)
    for intent in registry.intents:
        for trigger in intent.triggers:
            if trigger.starts_workflow and trigger.pattern.search(text):
                return trigger.starts_workflow
    return None


def continue_workflow(candidates: list[IntentCandidate], workflow: str | None) -> list[IntentCandidate]:
    """Terme « contextual » : rattache les messages au flux en cours (choix d'implémentation)."""
    if workflow != "submission":
        return candidates
    absorbed = [item for item in candidates if item.intent_id in SUBMISSION_ABSORBED_INTENTS]
    others = [item for item in candidates if item.intent_id not in SUBMISSION_ABSORBED_INTENTS]
    if not candidates or (absorbed and not others):
        return [IntentCandidate("listing.submit", 1.0 if absorbed else MEDIUM_BAND, 0.0)]
    if not absorbed:
        # Rien de reconnu comme description : paiement, aide… gardent leur sens propre.
        return candidates
    merged = IntentCandidate(
        "listing.submit",
        round(sum(item.score for item in absorbed), 4),
        sum(item.matched_weight for item in absorbed),
    )
    return sorted([merged, *others], key=lambda item: (-item.score, -item.matched_weight, item.intent_id))


def self_test(registry: IntentRegistry) -> float:
    """Autotest de démarrage : un passage complet doit tenir sous 16 ms, sinon on échoue bruyamment."""
    started = time.perf_counter()
    for probe in SELF_TEST_PROBES:
        classify(registry, probe)
    elapsed_ms = (time.perf_counter() - started) * 1000 / len(SELF_TEST_PROBES)
    if elapsed_ms > STAGE1_BUDGET_MS:
        raise RuntimeError(
            f"Scout Stage 1 trop lent : {elapsed_ms:.2f} ms par requête (budget {STAGE1_BUDGET_MS} ms)."
        )
    return elapsed_ms
