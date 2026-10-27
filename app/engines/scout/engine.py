"""Meterless Scout Intent appliqué à Kwatsur.

Pipeline de la spécification (engines/scout-intent/AGENTS.md, dépôt Meterless, Apache-2.0) :
Sense → Interpret → Guard → Route → Recommend → contrat d'exécution signé.
Scout n'exécute rien : il décide, contrôle, oriente et signe. L'agent exécute ensuite,
outil par outil, après vérification du contrat (`ContractVerifier`).
"""

import logging
import secrets
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.engines.scout.contract import ContractVerifier, issue_contract
from app.engines.scout.guard import POLICY_PACK_VERSION, GuardResult, run_guard
from app.engines.scout.interpret import Clarification, Interpretation, interpret
from app.engines.scout.registry import IntentRegistry, load_registry
from app.engines.scout.sense import (
    LOW_BAND,
    IntentCandidate,
    classify,
    continue_workflow,
    detect_workflow_start,
)

logger = logging.getLogger("kwatsur.scout")

# Graphe des capacités : capacité abstraite → outil concret de Kwatsur.
# Une capacité sans outil fait échouer l'orientation (jamais de substitution silencieuse).
CAPABILITY_GRAPH: dict[str, str] = {
    "listings.search": "search_service.search",
    "reply.explain": "llm.write_reply",
    "listings.compare": "comparison.build",
    "contact.draft": "contact_service.build_contact_draft",
    "reply.redirect": "template.redirect",
    "submission.collect": "submission_service.apply",
    "images.show": "image_service.owner_photos",
    "images.generate": "image_service.generate_illustration",
}
OFFLINE_FALLBACKS = {"llm.write_reply": "template.explain"}


@dataclass(frozen=True)
class ModelProfile:
    provider: str
    model: str
    available: bool


@dataclass(frozen=True)
class ScoutDecision:
    trace_id: str
    intent_id: str
    intent_label: str
    confidence: float
    band: str
    parameters: dict
    candidates: list[IntentCandidate]
    risk: GuardResult
    clarification: Clarification | None = None
    tool_plan: list[dict] = field(default_factory=list)
    contract: dict | None = None
    refusal_reason: str | None = None
    latency_ms: float = 0.0

    @property
    def proceeds(self) -> bool:
        return self.contract is not None


class ScoutEngine:
    def __init__(
        self,
        model_profile: ModelProfile,
        signing_secret: str = "",
        registry: IntentRegistry | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.registry = registry or load_registry()
        self.model_profile = model_profile
        # Sans secret configuré, un secret éphémère suffit : le contrat ne quitte pas la requête.
        self.secret = (signing_secret or secrets.token_hex(32)).encode("utf-8")
        self.now = now
        self.verifier = ContractVerifier(self.secret, now=now)

    def decide(
        self,
        prompt: str,
        surface: str = "chat",
        role: str = "visitor",
        user: str = "anonymous",
        has_active_search: bool = False,
        active_workflow: str | None = None,
        search_in_progress: bool = False,
    ) -> ScoutDecision:
        """`active_workflow` : « submission » quand un propriétaire est en train de décrire son logement.

        `has_active_search` : des résultats existent (comparer, visualiser…).
        `search_in_progress` : une recherche est commencée mais incomplète (ville encore demandée) ;
        une réponse sans mot-clé (« je suis à Bastos ») en est alors la suite.
        """
        started = time.perf_counter()
        trace_id = uuid.uuid4().hex

        candidates = classify(self.registry, prompt, has_active_search or search_in_progress)  # Sense
        workflow = active_workflow or detect_workflow_start(self.registry, prompt)
        candidates = continue_workflow(candidates, workflow)
        interpretation = interpret(self.registry, prompt, candidates, has_active_search)  # Interpret
        competing = tuple(item.intent_id for item in candidates if item.score >= LOW_BAND)
        risk = run_guard(prompt, interpretation.intent, surface, role, competing)      # Guard

        decision_fields = {
            "trace_id": trace_id,
            "intent_id": interpretation.intent.id,
            "intent_label": interpretation.intent.label,
            "confidence": interpretation.confidence,
            "band": interpretation.band,
            "parameters": interpretation.parameters,
            "candidates": candidates,
            "risk": risk,
        }
        if risk.blocked:
            decision = ScoutDecision(**decision_fields, refusal_reason=risk.reason)
        elif interpretation.clarification:
            decision = ScoutDecision(**decision_fields, clarification=interpretation.clarification)
            logger.info(
                "scout.clarification traceId=%s trigger=%s", trace_id, interpretation.clarification.trigger
            )
        else:
            tool_plan = self._route(interpretation)                                    # Route
            if tool_plan is None:
                decision = ScoutDecision(
                    **decision_fields, refusal_reason="Aucun outil autorisé ne permet cette action."
                )
            else:
                contract = self._recommend(interpretation, risk, tool_plan, trace_id, surface, user)
                decision = ScoutDecision(**decision_fields, tool_plan=tool_plan, contract=contract)

        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.info(
            "scout.decision traceId=%s intent=%s band=%s risk=%s latencyMs=%s stage2=skipped",
            trace_id, decision.intent_id, decision.band, risk.level, latency_ms,
        )
        return ScoutDecision(**{**decision.__dict__, "latency_ms": latency_ms})

    def _route(self, interpretation: Interpretation) -> list[dict] | None:
        plan = []
        for capability in interpretation.intent.capabilities:
            tool = CAPABILITY_GRAPH.get(capability)
            if tool is None:
                return None
            if tool in OFFLINE_FALLBACKS and not self.model_profile.available:
                tool = OFFLINE_FALLBACKS[tool]  # Outil local quand le modèle n'est pas configuré.
            plan.append({"capability": capability, "tool": tool, "input": interpretation.parameters})
        return plan

    def _recommend(
        self,
        interpretation: Interpretation,
        risk: GuardResult,
        tool_plan: list[dict],
        trace_id: str,
        surface: str,
        user: str,
    ) -> dict:
        fields = {
            "traceId": trace_id,
            "intent": {
                "primary": interpretation.intent.id,
                "parameters": interpretation.parameters,
                "references": {},
                "confidence": interpretation.confidence,
                "alternates": [
                    {"intent": item.intent_id, "score": item.score} for item in interpretation.alternates
                ],
            },
            "risk": {"level": risk.level, "flags": risk.flags, "redactions": risk.redactions, "approvals": []},
            "toolPlan": tool_plan,
            "modelProfile": {
                "provider": self.model_profile.provider,
                "model": self.model_profile.model,
            },
            "scope": {
                "user": user,
                "surface": surface,
                "capabilities": list(interpretation.intent.capabilities),
            },
            "registryVersion": self.registry.version,
            "policyPackVersion": POLICY_PACK_VERSION,
        }
        return issue_contract(fields, self.secret, self.now())
