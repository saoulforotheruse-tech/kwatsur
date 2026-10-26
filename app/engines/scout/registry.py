"""Catalogue des intentions (« intent registry ») de Scout Intent.

Une intention absente du catalogue ne peut déclencher aucune action. Forme du registre :
engines/scout-intent/docs/intent-registry.md du dépôt Meterless (Apache-2.0). Le champ
`triggers` (mots déclencheurs pondérés de l'étape Sense) et `requiresActiveSearch` sont
propres à Kwatsur.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

RiskClass = Literal["low", "medium", "high"]
GENERAL_INTENT_ID = "general.help"
REGISTRY_PATH = Path(__file__).with_name("kwatsur_intents.json")


def normalize_prompt(text: str) -> str:
    """Minuscules, sans accents ni caractères de contrôle, espaces réduits."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", without_accents).strip()


@dataclass(frozen=True)
class Trigger:
    pattern: re.Pattern[str]
    weight: float


@dataclass(frozen=True)
class Intent:
    id: str
    category: str
    label: str
    description: str
    parameters: dict
    capabilities: tuple[str, ...]
    risk_class: RiskClass
    surfaces: tuple[str, ...]
    roles: tuple[str, ...]
    requires_active_search: bool
    examples: tuple[str, ...]
    triggers: tuple[Trigger, ...]
    version: int

    @property
    def required_parameters(self) -> tuple[str, ...]:
        return tuple(self.parameters.get("required", ()))


@dataclass(frozen=True)
class IntentRegistry:
    version: int
    intents: tuple[Intent, ...]

    def get(self, intent_id: str) -> Intent:
        for intent in self.intents:
            if intent.id == intent_id:
                return intent
        raise KeyError(intent_id)


def parse_registry(payload: dict) -> IntentRegistry:
    intents = []
    for item in payload["intents"]:
        if not item.get("examples"):
            # Règle de la spécification : sans exemples, une intention n'est ni classable ni évaluable.
            raise ValueError(f"L'intention {item['id']} n'a pas d'exemples.")
        intents.append(
            Intent(
                id=item["id"],
                category=item["category"],
                label=item["label"],
                description=item["description"],
                parameters=item["parameters"],
                capabilities=tuple(item["capabilities"]),
                risk_class=item["riskClass"],
                surfaces=tuple(item["surfaces"]),
                roles=tuple(item["roles"]),
                requires_active_search=bool(item.get("requiresActiveSearch", False)),
                examples=tuple(item["examples"]),
                triggers=tuple(
                    Trigger(re.compile(trigger["pattern"]), float(trigger["weight"]))
                    for trigger in item["triggers"]
                ),
                version=int(item["version"]),
            )
        )
    registry = IntentRegistry(version=int(payload["registryVersion"]), intents=tuple(intents))
    registry.get(GENERAL_INTENT_ID)  # L'intention sûre par défaut doit exister.
    return registry


@lru_cache(maxsize=1)
def load_registry(path: Path = REGISTRY_PATH) -> IntentRegistry:
    return parse_registry(json.loads(path.read_text(encoding="utf-8")))
