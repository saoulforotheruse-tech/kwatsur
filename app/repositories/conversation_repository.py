"""Accès aux conversations persistées."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_session_id(self, session_id: str) -> Conversation | None:
        return self.session.scalar(
            select(Conversation).where(Conversation.session_id == session_id)
        )

    def create(self) -> Conversation:
        conversation = Conversation(search_criteria={})
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def recent_messages(self, conversation: Conversation, limit: int) -> list[Message]:
        """Derniers messages, du plus ancien au plus récent."""
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        return list(reversed(self.session.scalars(statement).all()))

    def all_messages(self, conversation: Conversation) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at, Message.id)
        )
        return list(self.session.scalars(statement))

    def add_message(self, conversation: Conversation, role: str, content: str) -> Message:
        message = Message(conversation_id=conversation.id, role=role, content=content)
        self.session.add(message)
        return message

    def save_criteria(self, conversation: Conversation, criteria: dict[str, Any]) -> None:
        conversation.search_criteria = criteria

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
