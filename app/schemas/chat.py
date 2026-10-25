"""Contrats Pydantic des échanges avec l'agent."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.criteria import SearchCriteria
from app.schemas.property import DataSourceName, PropertySearchResult

ReplyAuthor = Literal["nemotron", "meterless", "template"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)


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


class MessageRead(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationRead(BaseModel):
    conversation_id: str
    criteria: SearchCriteria
    messages: list[MessageRead]
