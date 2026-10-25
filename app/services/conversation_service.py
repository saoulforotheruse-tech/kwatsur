"""Gestion des conversations : historique, critères mémorisés et persistance."""

from app.core.exceptions import ConversationNotFoundError
from app.integrations.llm.base import ChatTurn
from app.models.conversation import Conversation
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.chat import ConversationRead, MessageRead
from app.schemas.criteria import SearchCriteria

HISTORY_WINDOW = 8  # Messages transmis au modèle pour garder le contexte utile.


class ConversationService:
    def __init__(self, repository: ConversationRepository) -> None:
        self.repository = repository

    def get_or_create(self, conversation_id: str | None) -> Conversation:
        if conversation_id is None:
            return self.repository.create()
        conversation = self.repository.get_by_session_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError()
        return conversation

    @staticmethod
    def current_criteria(conversation: Conversation) -> SearchCriteria:
        return SearchCriteria.model_validate(conversation.search_criteria or {})

    def recent_history(self, conversation: Conversation) -> list[ChatTurn]:
        if conversation.id is None:
            return []
        return [
            ChatTurn(role=message.role, content=message.content)
            for message in self.repository.recent_messages(conversation, HISTORY_WINDOW)
        ]

    def record_exchange(
        self,
        conversation: Conversation,
        user_message: str,
        assistant_reply: str,
        criteria: SearchCriteria,
    ) -> None:
        try:
            self.repository.add_message(conversation, "user", user_message)
            self.repository.add_message(conversation, "assistant", assistant_reply)
            self.repository.save_criteria(conversation, criteria.model_dump())
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

    def read(self, conversation_id: str) -> ConversationRead:
        conversation = self.repository.get_by_session_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError()
        return ConversationRead(
            conversation_id=conversation.session_id,
            criteria=self.current_criteria(conversation),
            messages=[
                MessageRead(role=message.role, content=message.content, created_at=message.created_at)
                for message in self.repository.all_messages(conversation)
            ],
        )
