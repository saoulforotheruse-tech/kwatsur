"""Harnais d'évaluation de Scout Intent, en Python.

Le lanceur officiel (engines/scout-intent/evals, `npm run evals`) attend une implémentation
JavaScript ; ce module en reprend les métriques et les seuils (evals/scout/thresholds.json)
pour l'implémentation Python de Kwatsur. Jeux de données : evals/scout/regression_v1/.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.engines.scout.engine import CAPABILITY_GRAPH, ModelProfile, ScoutEngine

EVALS_DIRECTORY = Path(__file__).resolve().parents[3] / "evals" / "scout"


@dataclass
class EvalReport:
    metrics: dict[str, float]
    slices: dict[str, dict[str, float]]
    failures: list[str] = field(default_factory=list)
    misses: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


def _load(name: str) -> list[dict]:
    path = EVALS_DIRECTORY / "regression_v1" / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def run_evals(engine: ScoutEngine | None = None) -> EvalReport:
    engine = engine or ScoutEngine(ModelProfile("eval", "none", True), "secret-d-evaluation")
    thresholds = json.loads((EVALS_DIRECTORY / "thresholds.json").read_text(encoding="utf-8"))
    misses: list[str] = []

    # Intentions : top-1, top-3, outil choisi, taux de clarification, par famille d'intention.
    top1 = top3 = clarified = tool_hits = tool_total = 0
    per_family: dict[str, list[int]] = {}
    intents = _load("intents.jsonl")
    for case in intents:
        decision = engine.decide(case["prompt"], has_active_search=case["active_search"])
        expected = case["expected"]["intent"]
        ranked = [candidate.intent_id for candidate in decision.candidates] or [decision.intent_id]
        hit = ranked[0] == expected
        top1 += hit
        top3 += expected in ranked[:3]
        per_family.setdefault(expected.split(".")[0], []).append(int(hit))
        clarified += decision.clarification is not None
        if decision.tool_plan:
            tool_total += 1
            expected_tool = CAPABILITY_GRAPH[engine.registry.get(expected).capabilities[0]]
            tool_hits += decision.tool_plan[0]["tool"] == expected_tool
        if "risk" in case["expected"] and decision.risk.level != case["expected"]["risk"]:
            misses.append(f"{case['id']}: risque {decision.risk.level} au lieu de {case['expected']['risk']}")
        if not hit:
            misses.append(f"{case['id']}: {ranked[0]} au lieu de {expected}")

    # Injections : jeu officiel Meterless (anglais) + jeu Kwatsur (français).
    true_positive = false_positive = false_negative = 0
    for case in _load("injection_meterless_v1.jsonl") + _load("injection_kwatsur.jsonl"):
        decision = engine.decide(case["prompt"])
        detected = any(flag["kind"] == "injection" for flag in decision.risk.flags)
        expected_injection = case["expected"]["injection"]
        true_positive += detected and expected_injection
        false_positive += detected and not expected_injection
        false_negative += expected_injection and not detected
        if detected != expected_injection:
            misses.append(f"{case['id']}: injection {'détectée' if detected else 'manquée'}")

    # Cas limites : clarification attendue ou non, déclencheur, intention, niveau de risque.
    edge_hits = 0
    edge_cases = _load("edge_cases.jsonl")
    for case in edge_cases:
        decision = engine.decide(case["prompt"], has_active_search=case["active_search"])
        expected = case["expected"]
        ok = True
        if "clarification" in expected:
            ok &= (decision.clarification is not None) == expected["clarification"]
        if "trigger" in expected:
            ok &= decision.clarification is not None and decision.clarification.trigger == expected["trigger"]
        if "intent" in expected:
            ok &= decision.intent_id == expected["intent"]
        if "risk" in expected:
            ok &= decision.risk.level == expected["risk"]
        edge_hits += ok
        if not ok:
            misses.append(f"{case['id']}: cas limite non respecté")

    metrics = {
        "intent_top1": _ratio(top1, len(intents)),
        "intent_top3_recall": _ratio(top3, len(intents)),
        "injection_precision": _ratio(true_positive, true_positive + false_positive),
        "injection_recall": _ratio(true_positive, true_positive + false_negative),
        "tool_precision": _ratio(tool_hits, tool_total),
        "clarification_rate": _ratio(clarified, len(intents)),
        "edge_case_accuracy": _ratio(edge_hits, len(edge_cases)),
    }
    slices = {"intent_top1": {family: _ratio(sum(hits), len(hits)) for family, hits in per_family.items()}}

    failures = []
    for name, limits in thresholds["metrics"].items():
        if "hard_floor" in limits and metrics[name] < limits["hard_floor"]:
            failures.append(f"{name}={metrics[name]} < plancher {limits['hard_floor']}")
        if "hard_max" in limits and metrics[name] > limits["hard_max"]:
            failures.append(f"{name}={metrics[name]} > plafond {limits['hard_max']}")
    slice_floor = thresholds["slice_policy"]["intent_top1"]["slice_hard_floor"]
    for family, value in slices["intent_top1"].items():
        if value < slice_floor:
            failures.append(f"intent_top1[{family}]={value} < plancher de tranche {slice_floor}")
    return EvalReport(metrics, slices, failures, misses)
