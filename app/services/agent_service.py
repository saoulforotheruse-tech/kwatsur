"""Orchestration de l'agent Kwatsur.

Flux d'un message :
  1. charger la conversation et ses critères ;
  2. Scout Intent (moteur Meterless) classe l'intention, contrôle les risques et signe un
     contrat d'exécution ; sans contrat (blocage ou clarification), aucun outil n'agit ;
  3. selon l'intention : recherche, comparaison, brouillon de contact ou redirection,
     chaque outil vérifiant le contrat avant d'agir ;
  4. pour une recherche : extraction des critères par le modèle, fusion et validation,
     question si la ville manque, sinon recherche, filtres, classement, risques, puis
     explication rédigée par le modèle à partir des seuls faits calculés ;
  5. enregistrer l'échange et renvoyer réponse + logements structurés + trace Scout.
"""

import logging

from app.core.exceptions import KwatsurError
from app.engines.scout import ScoutDecision, ScoutEngine
from app.integrations.llm.base import LLMProvider, ReplyContext
from app.models.conversation import Conversation
from app.schemas.chat import ChatResponse, ReplyAuthor, ScoutTrace
from app.schemas.criteria import SearchCriteria
from app.schemas.property import DataSourceName, PropertySearchResult
from app.services.comparison_service import build_comparison
from app.services.contact_service import build_contact_draft
from app.services.conversation_service import ConversationService
from app.services.criteria_service import merge_criteria, relaxation_suggestions
from app.services.ranking_service import format_fcfa
from app.services.search_service import SearchOutcome, SearchService

logger = logging.getLogger(__name__)

RESULTS_RETURNED = 10
RESULTS_EXPLAINED = 5
DEFAULT_CITY_QUESTION = "Dans quelle ville cherchez-vous un logement (par exemple Douala ou Yaoundé) ?"
OFF_TOPIC_REPLY = (
    "Je suis spécialisé dans la recherche de logements à louer au Cameroun. "
    "Décrivez-moi ce que vous cherchez : ville, quartier, budget, nombre de chambres…"
)
PAYMENT_REFUSAL = (
    "Je ne fais aucun paiement ni transfert d'argent. Ne versez jamais d'avance ni de caution "
    "avant d'avoir visité le logement et vérifié l'identité du bailleur."
)
DEMO_MODE_NOTICE = "Mode démo sans IA : critères compris par des règles, explication générée par le code."
BLOCKED_REPLY = "Je ne peux pas traiter cette demande. Décrivez simplement le logement que vous cherchez."


def scout_trace(decision: ScoutDecision) -> ScoutTrace:
    """Résumé de la décision Scout renvoyé au frontend : intention, risque, contrat, modèle."""
    contract = decision.contract
    return ScoutTrace(
        trace_id=decision.trace_id,
        intent=decision.intent_id,
        confidence=decision.confidence,
        band=decision.band,
        risk_level=decision.risk.level,
        risk_flags=[flag["kind"] for flag in decision.risk.flags],
        contract_id=contract["contractId"] if contract else None,
        tool_plan=[step["tool"] for step in decision.tool_plan],
        model=contract["modelProfile"]["model"] if contract else None,
        clarification_options=decision.clarification.options if decision.clarification else [],
        latency_ms=decision.latency_ms,
    )


def clarification_reply(decision: ScoutDecision) -> str:
    clarification = decision.clarification
    options = [
        f"{index}. {option[0].upper()}{option[1:]}"
        for index, option in enumerate(clarification.options, 1)
    ]
    return "\n".join([clarification.question, *options])


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
        scout: ScoutEngine,
    ) -> None:
        self.llm = llm_provider
        self.search_service = search_service
        self.conversations = conversation_service
        self.scout = scout

    def handle_message(self, message: str, conversation_id: str | None) -> ChatResponse:
        conversation = self.conversations.get_or_create(conversation_id)
        current = self.conversations.current_criteria(conversation)
        session_id = conversation.session_id

        decision = self.scout.decide(message, has_active_search=current.city is not None)
        if not decision.proceeds:
            response = self._answer_without_contract(session_id, current, decision)
        elif decision.intent_id == "housing.search":
            response = self._handle_search(session_id, message, current, conversation, decision)
        elif decision.intent_id == "housing.compare":
            response = self._compare(session_id, current, decision)
        elif decision.intent_id == "contact.draft":
            response = self._draft_contact(session_id, current, decision)
        else:
            self.scout.verifier.require(decision.contract, "reply.redirect")
            response = self._answer_without_search(session_id, current, OFF_TOPIC_REPLY, "template", [])

        response.scout = scout_trace(decision)
        self.conversations.record_exchange(conversation, message, response.reply, response.criteria)
        return response

    def _answer_without_contract(
        self, session_id: str, criteria: SearchCriteria, decision: ScoutDecision
    ) -> ChatResponse:
        if decision.clarification:
            return self._answer_without_search(
                session_id, criteria, clarification_reply(decision), "template", []
            )
        reply = PAYMENT_REFUSAL if decision.intent_id == "payment.send" else BLOCKED_REPLY
        response = self._answer_without_search(session_id, criteria, reply, "template", [])
        response.needs_clarification = False
        return response

    def _handle_search(
        self,
        session_id: str,
        message: str,
        current: SearchCriteria,
        conversation: Conversation,
        decision: ScoutDecision,
    ) -> ChatResponse:
        history = self.conversations.recent_history(conversation)
        # Les erreurs d'extraction remontent : sans compréhension fiable, on ne cherche pas.
        extraction = self.llm.extract_criteria(message, history, current)
        criteria, notices = merge_criteria(current, extraction)

        if extraction.intent == "other" and criteria.is_empty():
            return self._answer_without_search(session_id, criteria, OFF_TOPIC_REPLY, "template", notices)
        if criteria.city is None:
            question = extraction.clarification_question
            author: ReplyAuthor = self.llm.name if question else "template"
            return self._answer_without_search(
                session_id, criteria, question or DEFAULT_CITY_QUESTION, author, notices
            )
        return self._search_and_explain(
            session_id, message, criteria, extraction.clarification_question, notices, decision
        )

    def _ranked_results(
        self, criteria: SearchCriteria, decision: ScoutDecision
    ) -> tuple[list[PropertySearchResult], DataSourceName]:
        """Relance la recherche courante pour retrouver les logements par leur rang."""
        self.scout.verifier.require(decision.contract, "listings.search")
        outcome = self.search_service.search(criteria, limit=RESULTS_RETURNED)
        return outcome.results, outcome.data_source

    def _compare(
        self, session_id: str, criteria: SearchCriteria, decision: ScoutDecision
    ) -> ChatResponse:
        results, data_source = self._ranked_results(criteria, decision)
        self.scout.verifier.require(decision.contract, "listings.compare")
        wanted = decision.parameters["ranks"]
        selected = [result for result in results if result.rank in wanted]
        if len(selected) < 2:
            reply = (
                "Il faut au moins deux logements à comparer ; "
                f"la recherche actuelle en compte {len(results)}."
            )
        else:
            reply = build_comparison(selected)
        return self._answer_with_results(session_id, criteria, reply, selected, data_source)

    def _draft_contact(
        self, session_id: str, criteria: SearchCriteria, decision: ScoutDecision
    ) -> ChatResponse:
        results, data_source = self._ranked_results(criteria, decision)
        self.scout.verifier.require(decision.contract, "contact.draft")
        rank = decision.parameters["rank"]
        selected = [result for result in results if result.rank == rank]
        if selected:
            draft = build_contact_draft(selected[0].property)
            reply = f"{draft.message}\n\n{draft.notice}"
        else:
            reply = f"Il n'y a pas de logement n°{rank} dans la recherche actuelle ({len(results)} résultat(s))."
        return self._answer_with_results(session_id, criteria, reply, selected, data_source)

    def _answer_with_results(
        self,
        session_id: str,
        criteria: SearchCriteria,
        reply: str,
        results: list[PropertySearchResult],
        data_source: DataSourceName,
    ) -> ChatResponse:
        return ChatResponse(
            conversation_id=session_id,
            reply=reply,
            reply_generated_by="template",
            criteria=criteria,
            needs_clarification=False,
            searched=True,
            total=len(results),
            data_source=data_source,
            results=results,
        )

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
        decision: ScoutDecision,
    ) -> ChatResponse:
        self.scout.verifier.require(decision.contract, "listings.search")
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
        self.scout.verifier.require(decision.contract, "reply.explain")
        explain_tool = next(step["tool"] for step in decision.tool_plan if step["capability"] == "reply.explain")
        if explain_tool == "template.explain":
            # Scout a choisi l'outil local : aucun modèle n'est configuré (mode démo).
            reply = build_template_reply(context)
            author = "template"
            notices.append(DEMO_MODE_NOTICE)
            return self._explained_response(session_id, reply, author, criteria, follow_up_question, outcome, notices)
        try:
            reply = self.llm.write_reply(context)
        except KwatsurError as error:
            # Les résultats sont déjà calculés : on les explique sans IA, en le signalant.
            logger.warning("Rédaction IA impossible, réponse de secours : %s", error)
            reply = build_template_reply(context)
            author = "template"
            notices.append("Explication rédigée sans IA : le modèle était indisponible.")
        return self._explained_response(session_id, reply, author, criteria, follow_up_question, outcome, notices)

    @staticmethod
    def _explained_response(
        session_id: str,
        reply: str,
        author: ReplyAuthor,
        criteria: SearchCriteria,
        follow_up_question: str | None,
        outcome: SearchOutcome,
        notices: list[str],
    ) -> ChatResponse:
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
