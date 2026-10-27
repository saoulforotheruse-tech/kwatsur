"""Orchestration de l'agent Kwatsur.

Flux d'un message :
  1. charger la conversation et ses critères ;
  2. Scout Intent (moteur Meterless) classe l'intention, contrôle les risques et signe un
     contrat d'exécution ; sans contrat (blocage ou clarification), aucun outil n'agit ;
  3. selon l'intention : recherche, comparaison, brouillon de contact, proposition d'annonce
     par un propriétaire, images d'une pièce ou redirection, chaque outil vérifiant le
     contrat avant d'agir ;
  4. pour une recherche : extraction des critères par le modèle, fusion et validation,
     question si la ville manque, sinon recherche, filtres, classement, risques, puis
     explication rédigée par le modèle à partir des seuls faits calculés ;
  5. enregistrer l'échange et renvoyer réponse + logements structurés + trace Scout.
"""

import logging
import re

from app.core.exceptions import KwatsurError
from app.engines.scout import ScoutDecision, ScoutEngine
from app.engines.scout.interpret import bind_ranks
from app.integrations.llm.base import ChatTurn, LLMProvider, ReplyContext
from app.models.conversation import Conversation
from app.schemas.chat import ChatResponse, ReplyAuthor, ScoutTrace
from app.schemas.criteria import KNOWN_NEIGHBORHOODS, SearchCriteria, normalize_text
from app.schemas.image import ROOM_LABELS
from app.schemas.property import DataSourceName, PropertyRead, PropertySearchResult
from app.services.comparison_service import build_comparison
from app.services.contact_service import build_contact_draft
from app.services.conversation_service import ConversationService
from app.services.criteria_service import merge_criteria, relaxation_suggestions
from app.services.image_service import ImageService
from app.services.ranking_service import format_fcfa
from app.services.search_service import SearchOutcome, SearchService
from app.services.small_talk import small_talk_reply
from app.services.submission_service import SubmissionService, fields_of

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
FEATURE_UNAVAILABLE_REPLY = "Cette fonctionnalité n'est pas disponible sur ce serveur."
DEMO_TAG = "[DÉMO — annonce fictive]"
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
        # Texte de l'annonce tel que fourni par la source : permet de répondre à « a-t-elle une cour ? ».
        "description": listing.description,
        "location_description": listing.location_description,
        "reasons": result.reasons,
        "tradeoffs": result.tradeoffs,
        "to_verify": result.to_verify,
        "risk_signals": result.risk_signals,
        "images": [
            image.model_dump(include={
                "id", "url", "kind", "room", "label", "is_ai_generated",
                "caption", "property_id", "credit", "source_url",
            })
            for image in result.images
        ],
    }


def named_visualization_results(
    message: str, results: list[PropertySearchResult],
) -> list[PropertySearchResult] | None:
    """Un nom explicite prime sur le premier résultat ; aucune substitution silencieuse."""
    def normalized(value: str) -> str:
        return " ".join(re.sub(r"[^\w\s]", " ", normalize_text(value)).split())

    text = normalized(message)
    names = {normalized(name) for name, _city in KNOWN_NEIGHBORHOODS.values()}
    names.update(normalized(result.property.title) for result in results)
    names.update(normalized(result.property.neighborhood) for result in results if result.property.neighborhood)
    mentioned = {name for name in names if f" {name} " in f" {text} "}
    if not mentioned:
        # Une référence nommée inconnue doit être clarifiée, pas remplacée par le n°1.
        if re.search(r"\b(?:celui|celle)\s+(?:de|du|a)\s+\w+", text):
            return []
        return None
    return [
        result for result in results
        if any(
            f" {name} " in f" {normalized(result.property.title)} "
            or name == normalized(result.property.neighborhood or "")
            for name in mentioned
        )
    ]


def illustration_brief(listing: PropertyRead) -> str:
    """Description transmise au générateur d'images : seulement le texte réel de l'annonce."""
    description = (listing.description or "").replace(DEMO_TAG, "").strip()
    return description or listing.title


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
        submissions: SubmissionService | None = None,
        images: ImageService | None = None,
        scout_routing: bool = True,
    ) -> None:
        self.llm = llm_provider
        self.search_service = search_service
        self.conversations = conversation_service
        self.scout = scout
        self.submissions = submissions
        self.images = images
        # Sans classification : seules les demandes explicites ouvrent les outils spécialisés.
        self.scout_routing = scout_routing

    def handle_message(self, message: str, conversation_id: str | None) -> ChatResponse:
        conversation = self.conversations.get_or_create(conversation_id)
        current = self.conversations.current_criteria(conversation)
        session_id = conversation.session_id

        draft = self.submissions.open_draft(session_id) if self.submissions else None
        if not self.scout_routing:
            canned = small_talk_reply(message)
            if canned is not None:
                response = self._answer_without_search(session_id, current, canned, "template", [])
                self.conversations.record_exchange(conversation, message, response.reply, response.criteria)
                return response
            # Seul le début explicite d'une annonce (« je mets mon appartement en location ») est détecté.
            owner_flow = draft is not None or self.scout.starts_submission(message)
            intent = "listing.submit" if owner_flow else "housing.search"
            if not owner_flow and self.scout.requests_visualization(message):
                intent = "listing.visualize"
            decision = self.scout.authorize(message, intent, has_active_search=current.city is not None)
        else:
            decision = self.scout.decide(
                message,
                has_active_search=current.city is not None,
                active_workflow="submission" if draft else None,
                search_in_progress=not current.is_empty(),
            )
        if not decision.risk.blocked and decision.intent_id != "listing.submit" and draft is None:
            visual_request = self.scout.requests_visualization(message)
            if visual_request and decision.intent_id != "listing.visualize":
                decision = self.scout.authorize(
                    message, "listing.visualize", has_active_search=current.city is not None
                )
            elif not visual_request and decision.intent_id == "listing.visualize":
                decision = self.scout.authorize(
                    message, "housing.search", has_active_search=current.city is not None
                )
        if not decision.proceeds:
            response = self._answer_without_contract(session_id, current, decision)
        elif decision.intent_id == "listing.submit":
            response = self._handle_submission(session_id, message, current, conversation, decision)
        elif decision.intent_id == "listing.visualize":
            response = self._visualize(session_id, current, decision, message)
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
            session_id, message, criteria, extraction.clarification_question, notices, decision, history
        )

    def _ranked_results(
        self, criteria: SearchCriteria, decision: ScoutDecision
    ) -> tuple[list[PropertySearchResult], DataSourceName]:
        """Relance la recherche courante pour retrouver les logements par leur rang."""
        self.scout.verifier.require(decision.contract, "listings.search")
        outcome = self.search_service.search(criteria, limit=RESULTS_RETURNED)
        return self._with_images(outcome.results), outcome.data_source

    def _with_images(self, results: list[PropertySearchResult]) -> list[PropertySearchResult]:
        return self.images.attach_photos(results) if self.images else results

    # --- Proposition d'annonce par un propriétaire --------------------------------------

    def _handle_submission(
        self,
        session_id: str,
        message: str,
        current: SearchCriteria,
        conversation: Conversation,
        decision: ScoutDecision,
    ) -> ChatResponse:
        if self.submissions is None:
            return self._answer_without_search(session_id, current, FEATURE_UNAVAILABLE_REPLY, "template", [])
        self.scout.verifier.require(decision.contract, "submission.collect")
        draft = self.submissions.open_draft(session_id) or self.submissions.start_draft(session_id)
        history = self.conversations.recent_history(conversation)
        extraction = self.llm.extract_listing(message, history, fields_of(draft))
        reply = self.submissions.apply(draft, extraction)
        response = self._answer_without_search(session_id, current, reply, "template", [])
        response.needs_clarification = draft.status == "draft"
        response.submission = self.submissions.to_read(draft)
        return response

    # --- Images d'une pièce : vraie photo d'abord, illustration IA sinon -----------------

    def _visualize(
        self, session_id: str, criteria: SearchCriteria, decision: ScoutDecision, message: str,
    ) -> ChatResponse:
        results, data_source = self._ranked_results(criteria, decision)
        rank, room = decision.parameters["rank"], decision.parameters["room"]
        named = named_visualization_results(message, results)
        if named is not None:
            explicit_ranks = bind_ranks(message)
            if explicit_ranks:
                named = [result for result in named if result.rank == explicit_ranks[0]]
            if len(named) != 1:
                options = " ; ".join(f"n°{result.rank} : {result.property.title}" for result in named)
                reply = (
                    "Plusieurs logements correspondent au nom indiqué. Précisez le numéro : " + options + "."
                    if named else
                    "Je ne trouve pas de logement correspondant à ce nom et à ce numéro éventuel "
                    "dans les résultats actuels. Précisez son numéro ou affinez la recherche."
                )
                response = self._answer_with_results(session_id, criteria, reply, named, data_source)
                response.needs_clarification = True
                return response
            selected = named
            rank = selected[0].rank
        else:
            selected = [result for result in results if result.rank == rank]
        if not selected:
            reply = f"Il n'y a pas de logement n°{rank} dans la recherche actuelle ({len(results)} résultat(s))."
            return self._answer_with_results(session_id, criteria, reply, [], data_source)
        if self.images is None:
            return self._answer_with_results(session_id, criteria, FEATURE_UNAVAILABLE_REPLY, selected, data_source)

        listing = selected[0].property
        room_label = ROOM_LABELS[room]
        self.scout.verifier.require(decision.contract, "images.show")
        photos = self.images.owner_photos(listing.id, room)
        if photos:
            reply = f"Voici la photo ({room_label}) fournie par le propriétaire du logement n°{rank}, « {listing.title} »."
            response = self._answer_with_results(session_id, criteria, reply, selected, data_source)
            response.images = photos
            return response

        samples = [
            image for image in selected[0].images
            if image.kind == "sample_photo" and image.room == room
        ]
        if samples:
            reply = (
                f"Voici une photo d'exemple ({room_label}) associée au logement n°{rank}, "
                f"« {listing.title} ». Ce n'est pas une photo de ce logement."
            )
            response = self._answer_with_results(session_id, criteria, reply, selected, data_source)
            response.images = samples
            return response

        existing = self.images.existing_illustration(listing.id, room)
        if existing is not None:
            # Déjà générée pour ce logement et cette pièce : réutilisée, sans consommer de quota.
            reply = (
                f"Le propriétaire du logement n°{rank}, « {listing.title} », n'a pas fourni de photo ({room_label}). "
                "Voici l'image illustrative déjà générée par IA pour cette pièce : elle ne représente "
                "pas le logement réel."
            )
            response = self._answer_with_results(session_id, criteria, reply, selected, data_source)
            response.images = [existing]
            return response

        self.scout.verifier.require(decision.contract, "images.generate")
        try:
            illustration = self.images.generate_illustration(illustration_brief(listing), room, listing)
        except KwatsurError as error:
            # Pas de photo et pas d'illustration possible : on le dit, sans rien inventer.
            reply = (
                f"Le propriétaire du logement n°{rank} n'a pas fourni de photo ({room_label}), "
                f"et aucune illustration n'a pu être générée : {error.public_message}"
            )
            return self._answer_with_results(session_id, criteria, reply, selected, data_source)
        sources = "de la description de l'annonce"
        if illustration.reference_photo_kind == "owner_photo":
            sources += f" et de {illustration.reference_photo_count} vraie(s) photo(s) du propriétaire"
        elif illustration.reference_photo_kind == "sample_photo":
            sources += (
                f" et de {illustration.reference_photo_count} photo(s) d'exemple de maisons "
                "camerounaises (pas de ce logement)"
            )
        reply = (
            f"Aucune photo du propriétaire n'est disponible pour cette pièce ({room_label}) "
            f"du logement n°{rank}, « {listing.title} ». "
            f"Voici une représentation illustrative générée par IA à partir {sources}, "
            "avec un contexte visuel camerounais. Elle ne représente pas le logement réel "
            "et peut s'en écarter."
        )
        response = self._answer_with_results(session_id, criteria, reply, selected, data_source)
        response.images = [illustration]
        return response

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
        history: list[ChatTurn],
    ) -> ChatResponse:
        self.scout.verifier.require(decision.contract, "listings.search")
        outcome = self.search_service.search(criteria, limit=RESULTS_RETURNED)
        outcome.results = self._with_images(outcome.results)
        notices = notices + outcome.notices
        context = ReplyContext(
            user_message=message,
            criteria=criteria,
            total_results=outcome.total,
            top_results=[summarize_for_model(item) for item in outcome.results[:RESULTS_EXPLAINED]],
            follow_up_question=follow_up_question,
            relaxation_suggestions=relaxation_suggestions(criteria) if outcome.total == 0 else [],
            notices=notices,
            conversation_history=history,
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
