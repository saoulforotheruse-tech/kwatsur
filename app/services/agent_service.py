"""Orchestration de l'agent Kwatsur.

Flux d'un message :
  1. charger la conversation et ses critères ;
  2. faire extraire les nouveaux critères par le modèle ;
  3. les fusionner et les valider côté backend ;
  4. poser une question si la ville manque, sinon rechercher, filtrer, classer et évaluer les risques ;
  5. faire rédiger l'explication par le modèle à partir des seuls faits calculés ;
  6. enregistrer l'échange et renvoyer réponse + logements structurés.
"""

import logging

from app.core.exceptions import KwatsurError
from app.integrations.llm.base import LLMProvider, ReplyContext
from app.schemas.chat import ChatResponse, ReplyAuthor
from app.schemas.criteria import SearchCriteria
from app.schemas.property import PropertySearchResult
from app.services.conversation_service import ConversationService
from app.services.criteria_service import merge_criteria, relaxation_suggestions
from app.services.ranking_service import format_fcfa
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)

RESULTS_RETURNED = 10
RESULTS_EXPLAINED = 5
DEFAULT_CITY_QUESTION = "Dans quelle ville cherchez-vous un logement (par exemple Douala ou Yaoundé) ?"
OFF_TOPIC_REPLY = (
    "Je suis spécialisé dans la recherche de logements à louer au Cameroun. "
    "Décrivez-moi ce que vous cherchez : ville, quartier, budget, nombre de chambres…"
)


def summarize_for_model(result: PropertySearchResult) -> dict:
    """Vue compacte d'un résultat : uniquement des faits issus de la source et du classement."""
    listing = result.property
    return {
        "rank": result.rank,
        "title": listing.title,
        "city": listing.city,
        "neighborhood": listing.neighborhood,
        "property_type": listing.property_type,
        "monthly_rent_fcfa": listing.monthly_rent,
        "bedrooms": listing.bedrooms,
        "source_name": listing.source_name,
        "source_is_demo": listing.source_is_demo,
        "listing_status": listing.listing_status,
        "reasons": result.reasons,
        "tradeoffs": result.tradeoffs,
        "to_verify": result.to_verify,
        "risk_signals": result.risk_signals,
    }


def build_template_reply(context: ReplyContext) -> str:
    """Réponse de secours rédigée par le code quand le modèle ne peut pas l'écrire."""
    if context.total_results == 0:
        lines = ["Je n'ai trouvé aucun logement correspondant à tous vos critères."]
        if context.relaxation_suggestions:
            lines.append("Vous pourriez essayer de " + " ou de ".join(context.relaxation_suggestions[:2]) + ".")
    else:
        lines = [f"J'ai trouvé {context.total_results} logement(s) correspondant à vos critères."]
        for result in context.top_results[:3]:
            demo = " (annonce de démonstration)" if result["source_is_demo"] else ""
            lines.append(
                f"{result['rank']}. {result['title']}{demo} : "
                f"{format_fcfa(result['monthly_rent_fcfa'])} par mois."
            )
            if result["to_verify"]:
                lines.append(f"   À vérifier : {result['to_verify'][0]}")
    if context.follow_up_question:
        lines.append(context.follow_up_question)
    return "\n".join(lines)


class AgentService:
    def __init__(
        self,
        llm_provider: LLMProvider,
        search_service: SearchService,
        conversation_service: ConversationService,
    ) -> None:
        self.llm = llm_provider
        self.search_service = search_service
        self.conversations = conversation_service

    def handle_message(self, message: str, conversation_id: str | None) -> ChatResponse:
        conversation = self.conversations.get_or_create(conversation_id)
        current = self.conversations.current_criteria(conversation)
        history = self.conversations.recent_history(conversation)

        # Les erreurs d'extraction remontent : sans compréhension fiable, on ne cherche pas.
        extraction = self.llm.extract_criteria(message, history, current)
        criteria, notices = merge_criteria(current, extraction)

        session_id = conversation.session_id
        if extraction.intent == "other" and criteria.is_empty():
            response = self._answer_without_search(
                session_id, criteria, OFF_TOPIC_REPLY, "template", notices
            )
        elif criteria.city is None:
            question = extraction.clarification_question
            author: ReplyAuthor = self.llm.name if question else "template"
            response = self._answer_without_search(
                session_id, criteria, question or DEFAULT_CITY_QUESTION, author, notices
            )
        else:
            response = self._search_and_explain(
                session_id, message, criteria, extraction.clarification_question, notices
            )

        self.conversations.record_exchange(conversation, message, response.reply, criteria)
        return response

    def _answer_without_search(
        self,
        session_id: str,
        criteria: SearchCriteria,
        reply: str,
        author: ReplyAuthor,
        notices: list[str],
    ) -> ChatResponse:
        return ChatResponse(
            conversation_id=session_id,
            reply=reply,
            reply_generated_by=author,
            criteria=criteria,
            needs_clarification=True,
            searched=False,
            notices=notices,
        )

    def _search_and_explain(
        self,
        session_id: str,
        message: str,
        criteria: SearchCriteria,
        follow_up_question: str | None,
        notices: list[str],
    ) -> ChatResponse:
        outcome = self.search_service.search(criteria, limit=RESULTS_RETURNED)
        notices = notices + outcome.notices
        context = ReplyContext(
            user_message=message,
            criteria=criteria,
            total_results=outcome.total,
            top_results=[summarize_for_model(item) for item in outcome.results[:RESULTS_EXPLAINED]],
            follow_up_question=follow_up_question,
            relaxation_suggestions=relaxation_suggestions(criteria) if outcome.total == 0 else [],
            notices=notices,
        )

        author: ReplyAuthor = self.llm.name
        try:
            reply = self.llm.write_reply(context)
        except KwatsurError as error:
            # Les résultats sont déjà calculés : on les explique sans IA, en le signalant.
            logger.warning("Rédaction IA impossible, réponse de secours : %s", error)
            reply = build_template_reply(context)
            author = "template"
            notices.append("Explication rédigée sans IA : le modèle était indisponible.")

        return ChatResponse(
            conversation_id=session_id,
            reply=reply,
            reply_generated_by=author,
            criteria=criteria,
            needs_clarification=follow_up_question is not None,
            searched=True,
            total=outcome.total,
            data_source=outcome.data_source,
            notices=notices,
            results=outcome.results,
        )
