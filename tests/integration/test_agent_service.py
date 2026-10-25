"""Agent complet sur SQLite (données fictives) avec un fournisseur IA simulé."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import IntegrationUnavailableError, InvalidIntegrationResponseError
from app.integrations.data.postgres import PostgresListingSource
from app.models.message import Message
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.property_repository import PropertyRepository
from app.services.agent_service import AgentService
from app.services.conversation_service import ConversationService
from app.services.ranking_service import RankingService
from app.services.risk_service import RiskService
from app.services.search_service import SearchService
from tests.fakes import MockLLMProvider, scripted_extractions


def make_agent(session: Session, llm: MockLLMProvider) -> AgentService:
    search = SearchService(
        PostgresListingSource(PropertyRepository(session)), RankingService(), RiskService()
    )
    return AgentService(llm, search, ConversationService(ConversationRepository(session)))


def count_messages(session: Session) -> int:
    return session.scalar(select(func.count(Message.id)))


def test_missing_city_triggers_a_question_without_search(session: Session) -> None:
    llm = MockLLMProvider(scripted_extractions(
        {"intent": "search", "updates": {"bedrooms": 2},
         "clarification_question": "Dans quelle ville cherchez-vous ?"}
    ))

    response = make_agent(session, llm).handle_message("Je veux deux chambres", None)

    assert response.searched is False
    assert response.needs_clarification is True
    assert response.reply == "Dans quelle ville cherchez-vous ?"
    assert response.criteria.bedrooms == 2


def test_conversation_keeps_criteria_and_history(session: Session) -> None:
    llm = MockLLMProvider(scripted_extractions(
        {"intent": "search", "updates": {"city": "Douala", "neighborhood": "Bonamoussadi",
                                         "bedrooms": 2, "max_rent": 150000}},
        {"intent": "refine", "updates": {"max_rent": 110000}},
    ))
    agent = make_agent(session, llm)

    first = agent.handle_message("Appartement 2 chambres à Bonamoussadi, 150 000 max", None)
    second = agent.handle_message("Finalement 110 000 maximum", first.conversation_id)

    assert second.conversation_id == first.conversation_id
    assert second.criteria.city == "Douala"
    assert second.criteria.bedrooms == 2
    assert second.criteria.max_rent == 110000
    assert all(item.property.monthly_rent <= 110000 for item in second.results)
    # Le modèle reçoit l'historique du premier échange au second message.
    assert [turn.role for turn in llm.received_histories[1]] == ["user", "assistant"]
    assert count_messages(session) == 4


def test_model_only_receives_verified_results(session: Session) -> None:
    llm = MockLLMProvider(scripted_extractions(
        {"intent": "search", "updates": {"city": "Douala", "max_rent": 150000, "bedrooms": 2}}
    ))

    response = make_agent(session, llm).handle_message("2 chambres à Douala", None)

    context = llm.received_contexts[0]
    sent_titles = [item["title"] for item in context.top_results]
    assert sent_titles == [item.property.title for item in response.results[: len(sent_titles)]]
    assert response.reply_generated_by == "nemotron"


def test_no_result_proposes_relaxing_criteria(session: Session) -> None:
    llm = MockLLMProvider(scripted_extractions(
        {"intent": "search", "updates": {"city": "Douala", "max_rent": 20000, "bedrooms": 4}}
    ))

    response = make_agent(session, llm).handle_message("4 chambres à 20 000", None)

    assert response.total == 0 and response.results == []
    assert llm.received_contexts[0].relaxation_suggestions


def test_reply_failure_falls_back_to_labelled_template(session: Session) -> None:
    llm = MockLLMProvider(
        scripted_extractions({"intent": "search", "updates": {"city": "Yaoundé"}}),
        reply_error=IntegrationUnavailableError("Quota atteint."),
    )

    response = make_agent(session, llm).handle_message("Un logement à Yaoundé", None)

    assert response.reply_generated_by == "template"
    assert response.total > 0
    assert any("sans IA" in notice for notice in response.notices)


def test_extraction_failure_is_raised_and_nothing_is_saved(session: Session) -> None:
    llm = MockLLMProvider(
        scripted_extractions(), extraction_error=InvalidIntegrationResponseError()
    )

    with pytest.raises(InvalidIntegrationResponseError):
        make_agent(session, llm).handle_message("Bonjour", None)

    assert count_messages(session) == 0


def test_off_topic_message_gets_a_redirect(session: Session) -> None:
    llm = MockLLMProvider(scripted_extractions({"intent": "other"}))

    response = make_agent(session, llm).handle_message("Quel temps fait-il ?", None)

    assert response.searched is False
    assert "logements" in response.reply
