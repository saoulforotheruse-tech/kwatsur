"""Contrats Pydantic des échanges avec l'agent."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.criteria import SearchCriteria
from app.schemas.image import ImageRead
from app.schemas.property import DataSourceName, PropertySearchResult
from app.schemas.submission import SubmissionRead

ReplyAuthor = Literal["nemotron", "meterless", "rules", "template"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)


class ScoutTrace(BaseModel):
    """Décision du moteur Meterless Scout Intent : preuve de ce qui a autorisé la réponse."""

    trace_id: str
    intent: str
    confidence: float
    band: str
    risk_level: str
    risk_flags: list[str] = Field(default_factory=list)
    contract_id: str | None = None
    tool_plan: list[str] = Field(default_factory=list)
    # Modèle désigné par le contrat (traçabilité demandée par le jury).
    model: str | None = None
    clarification_options: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    # Indique qui a rédigé la réponse : le modèle ou un gabarit déterministe de secours.
    reply_generated_by: ReplyAuthor
    criteria: SearchCriteria
    needs_clarification: bool
    searched: bool
    total: int = 0
    data_source: DataSourceName | None = None
    notices: list[str] = Field(default_factory=list)
    results: list[PropertySearchResult] = Field(default_factory=list)
    scout: ScoutTrace | None = None
    # Photos du propriétaire ou illustrations IA demandées dans ce message (toujours étiquetées).
    images: list[ImageRead] = Field(default_factory=list)
    # Proposition d'annonce en cours, quand l'utilisateur décrit son propre logement.
    submission: SubmissionRead | None = None


class MessageRead(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationRead(BaseModel):
    conversation_id: str
    criteria: SearchCriteria
    messages: list[MessageRead]
