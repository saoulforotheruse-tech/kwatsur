"""Fournisseur IA basé sur NVIDIA Nemotron (en direct ou via Meterless).

Le modèle extrait les critères et rédige l'explication. Il ne filtre ni ne classe :
ces opérations restent faites par le backend.
"""

import json
import logging
from dataclasses import asdict
from functools import cache
from pathlib import Path

from pydantic import ValidationError

from app.core.exceptions import IntegrationNotConfiguredError, InvalidIntegrationResponseError
from app.integrations.llm.base import ChatTurn, ReplyContext
from app.integrations.llm.openai_compatible import ChatCompletionClient
from app.schemas.chat import ReplyAuthor
from app.schemas.criteria import CriteriaExtraction, SearchCriteria
from app.schemas.submission import ListingExtraction, ListingFields

logger = logging.getLogger(__name__)

PROMPTS_DIRECTORY = Path(__file__).resolve().parents[2] / "prompts"
MAX_REPLY_LENGTH = 2500


@cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIRECTORY / name).read_text(encoding="utf-8")


def parse_json_object(text: str) -> dict:
    """Extrait le premier objet JSON d'une réponse, même entourée de texte ou de ```."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("Aucun objet JSON dans la réponse.")
    return json.loads(text[start : end + 1])


class NemotronProvider:
    def __init__(self, chat_client: ChatCompletionClient, name: ReplyAuthor = "nemotron") -> None:
        self.chat_client = chat_client
        self.name = name

    def extract_criteria(
        self, message: str, history: list[ChatTurn], current: SearchCriteria
    ) -> CriteriaExtraction:
        request = {
            "criteres_actuels": current.model_dump(),
            "conversation_recente": [asdict(turn) for turn in history],
            "nouveau_message": message,
        }
        messages = [
            {"role": "system", "content": load_prompt("criteria_extraction.md")},
            {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
        ]
        raw_answer = self.chat_client.complete(messages, temperature=0.0, max_tokens=4096)
        try:
            return CriteriaExtraction.model_validate(parse_json_object(raw_answer))
        except (ValueError, ValidationError):
            # Une seule relance, en rappelant le format attendu.
            logger.info("Extraction invalide, nouvelle tentative avec rappel du format.")
            messages += [
                {"role": "assistant", "content": raw_answer[:2000]},
                {"role": "user", "content": "Réponds uniquement avec l'objet JSON demandé, sans texte autour."},
            ]
            retry_answer = self.chat_client.complete(messages, temperature=0.0, max_tokens=4096)
            try:
                return CriteriaExtraction.model_validate(parse_json_object(retry_answer))
            except (ValueError, ValidationError) as error:
                raise InvalidIntegrationResponseError(
                    "Le modèle IA n'a pas renvoyé de critères exploitables."
                ) from error

    def extract_listing(
        self, message: str, history: list[ChatTurn], current: ListingFields
    ) -> ListingExtraction:
        request = {
            "annonce_actuelle": current.model_dump(),
            "conversation_recente": [asdict(turn) for turn in history],
            "nouveau_message": message,
        }
        messages = [
            {"role": "system", "content": load_prompt("listing_extraction.md")},
            {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
        ]
        raw_answer = self.chat_client.complete(messages, temperature=0.0, max_tokens=4096)
        try:
            return ListingExtraction.model_validate(parse_json_object(raw_answer))
        except (ValueError, ValidationError) as error:
            raise InvalidIntegrationResponseError(
                "Le modèle IA n'a pas renvoyé d'informations d'annonce exploitables."
            ) from error

    def write_reply(self, context: ReplyContext) -> str:
        facts = asdict(context)
        facts["criteria"] = context.criteria.model_dump()
        messages = [
            {"role": "system", "content": load_prompt("housing_agent.md")},
            {"role": "user", "content": json.dumps(facts, ensure_ascii=False, default=str)},
        ]
        reply = self.chat_client.complete(messages, temperature=0.3, max_tokens=4096)
        return reply[:MAX_REPLY_LENGTH]


class DisabledLLMProvider:
    """Utilisé quand LLM_PROVIDER=none : signale clairement l'absence d'IA."""

    name: ReplyAuthor = "nemotron"

    def extract_criteria(self, *_args: object) -> CriteriaExtraction:
        raise IntegrationNotConfiguredError("L'agent IA est désactivé (LLM_PROVIDER=none).")

    def write_reply(self, *_args: object) -> str:
        raise IntegrationNotConfiguredError("L'agent IA est désactivé (LLM_PROVIDER=none).")

    def extract_listing(self, *_args: object) -> ListingExtraction:
        raise IntegrationNotConfiguredError("L'agent IA est désactivé (LLM_PROVIDER=none).")
