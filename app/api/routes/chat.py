"""Routes HTTP pour les conversations avec l'agent."""

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    AgentServiceDependency,
    ConversationServiceDependency,
    enforce_chat_rate_limit,
)
from app.schemas.chat import ChatRequest, ChatResponse, ConversationRead

router = APIRouter(prefix="/api", tags=["agent"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(enforce_chat_rate_limit)],
    summary="Envoyer un message à l'agent Kwatsur",
)
def chat(request: ChatRequest, agent: AgentServiceDependency) -> ChatResponse:
    return agent.handle_message(request.message.strip(), request.conversation_id)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationRead,
    summary="Relire une conversation et ses critères mémorisés",
)
def get_conversation(
    conversation_id: str, conversations: ConversationServiceDependency
) -> ConversationRead:
    # L'identifiant est un UUID aléatoire : le connaître donne accès à la conversation.
    return conversations.read(conversation_id)
