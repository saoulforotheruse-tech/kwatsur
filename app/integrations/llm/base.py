"""Contrat commun des fournisseurs IA."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.schemas.chat import ReplyAuthor
from app.schemas.criteria import CriteriaExtraction, SearchCriteria
from app.schemas.submission import ListingExtraction, ListingFields


@dataclass(frozen=True)
class ChatTurn:
    role: str
    content: str


@dataclass
class ReplyContext:
    """Faits vérifiés transmis au modèle : il les explique sans rien y ajouter."""

    user_message: str
    criteria: SearchCriteria
    total_results: int
    top_results: list[dict[str, Any]]
    follow_up_question: str | None = None
    relaxation_suggestions: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    # Derniers messages : pour comprendre « elle », « le premier »… jamais comme source de faits.
    conversation_history: list[ChatTurn] = field(default_factory=list)


class LLMProvider(Protocol):
    name: ReplyAuthor

    def extract_criteria(
        self, message: str, history: list[ChatTurn], current: SearchCriteria
    ) -> CriteriaExtraction: ...

    def write_reply(self, context: ReplyContext) -> str: ...

    def extract_listing(
        self, message: str, history: list[ChatTurn], current: ListingFields
    ) -> ListingExtraction:
        """Informations d'annonce données par un propriétaire dans son message."""
        ...
