"""Doublures de test (MOCKS) : elles ne communiquent avec aucun service réel."""

from collections.abc import Callable

from app.core.exceptions import KwatsurError
from app.integrations.llm.base import ChatTurn, ReplyContext
from app.schemas.chat import ReplyAuthor
from app.schemas.criteria import CriteriaExtraction, SearchCriteria

ExtractionRule = Callable[[str, SearchCriteria], CriteriaExtraction]


class MockLLMProvider:
    """Fournisseur IA simulé : extraction scriptée, réponse construite à partir du contexte."""

    name: ReplyAuthor = "nemotron"

    def __init__(
        self,
        extraction_rule: ExtractionRule,
        extraction_error: KwatsurError | None = None,
        reply_error: KwatsurError | None = None,
    ) -> None:
        self.extraction_rule = extraction_rule
        self.extraction_error = extraction_error
        self.reply_error = reply_error
        self.received_histories: list[list[ChatTurn]] = []
        self.received_contexts: list[ReplyContext] = []

    def extract_criteria(
        self, message: str, history: list[ChatTurn], current: SearchCriteria
    ) -> CriteriaExtraction:
        self.received_histories.append(history)
        if self.extraction_error:
            raise self.extraction_error
        return self.extraction_rule(message, current)

    def write_reply(self, context: ReplyContext) -> str:
        self.received_contexts.append(context)
        if self.reply_error:
            raise self.reply_error
        return f"[réponse simulée] {context.total_results} résultat(s)."


def scripted_extractions(*extractions: dict) -> ExtractionRule:
    """Renvoie successivement les extractions fournies, une par message."""
    queue = [CriteriaExtraction.model_validate(item) for item in extractions]

    def rule(_message: str, _current: SearchCriteria) -> CriteriaExtraction:
        return queue.pop(0)

    return rule
