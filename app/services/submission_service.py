"""Proposition d'annonces par les propriétaires, puis validation par un administrateur.

Parcours :
  1. le propriétaire décrit son logement dans le chat ; chaque message complète un brouillon ;
  2. l'agent demande, une par une, les informations indispensables qui manquent ;
  3. une fois tout réuni, il résume et demande confirmation ; « oui » envoie la proposition
     (statut pending) ;
  4. un administrateur l'approuve (création d'une vraie annonce dans `properties`) ou la refuse.
Rien n'est visible des chercheurs avant l'approbation.
"""

from collections.abc import Callable
from datetime import datetime, timezone

from app.core.exceptions import KwatsurError
from app.models.property import Property
from app.models.submission import ListingSubmission
from app.repositories.image_repository import ImageRepository
from app.repositories.submission_repository import SubmissionRepository
from app.schemas.image import ImageRead
from app.schemas.submission import (
    FIELD_LABELS,
    FIELD_QUESTIONS,
    REQUIRED_FIELDS,
    ListingExtraction,
    ListingFields,
    SubmissionRead,
)
from app.services.image_service import ImageService
from app.services.ranking_service import format_fcfa

EDITABLE_FIELDS = tuple(ListingFields.model_fields)


class SubmissionNotFoundError(KwatsurError):
    status_code = 404
    public_message = "Proposition d'annonce introuvable."


class SubmissionStateError(KwatsurError):
    status_code = 409
    public_message = "Cette proposition ne peut plus être modifiée dans son état actuel."


def fields_of(submission: ListingSubmission) -> ListingFields:
    return ListingFields.model_validate({name: getattr(submission, name) for name in EDITABLE_FIELDS})


def missing_fields(submission: ListingSubmission) -> list[str]:
    return [name for name in REQUIRED_FIELDS if getattr(submission, name) is None]


def _display(name: str, value: object) -> str:
    if isinstance(value, bool):
        return "oui" if value else "non"
    if name == "monthly_rent":
        return f"{format_fcfa(value)} / mois"
    return str(value)


def summarize(submission: ListingSubmission) -> str:
    """Récapitulatif lisible des informations déjà connues (jamais de valeur inventée)."""
    lines = [
        f"- {FIELD_LABELS[name]} : {_display(name, getattr(submission, name))}"
        for name in FIELD_LABELS
        if getattr(submission, name) is not None
    ]
    return "\n".join(lines) if lines else "- (aucune information pour l'instant)"


def default_title(submission: ListingSubmission) -> str:
    kind = (submission.property_type or "Logement").capitalize()
    rooms = f" {submission.bedrooms} chambre(s)" if submission.bedrooms else ""
    return f"{kind}{rooms} à {submission.neighborhood or submission.city}"


class SubmissionService:
    def __init__(
        self,
        repository: SubmissionRepository,
        image_repository: ImageRepository,
        image_service: ImageService,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.repository = repository
        self.image_repository = image_repository
        self.image_service = image_service
        self.now = now

    # --- Côté propriétaire (chat) ------------------------------------------------------

    def open_draft(self, session_id: str) -> ListingSubmission | None:
        return self.repository.open_draft(session_id)

    def start_draft(self, session_id: str) -> ListingSubmission:
        return self.repository.add(ListingSubmission(session_id=session_id, status="draft"))

    def apply(self, submission: ListingSubmission, extraction: ListingExtraction) -> str:
        """Applique un message du propriétaire au brouillon et renvoie la réponse de l'agent."""
        if extraction.cancels:
            submission.status = "cancelled"
            return "C'est noté, j'abandonne cette proposition. Rien n'a été publié."

        for name, value in extraction.updates.model_dump(exclude_none=True).items():
            setattr(submission, name, value)
        # Un studio n'a pas de chambre séparée : inutile de poser la question.
        if submission.property_type == "studio" and submission.bedrooms is None:
            submission.bedrooms = 0

        missing = missing_fields(submission)
        if missing:
            return (
                "Merci, voici ce que j'ai noté :\n"
                f"{summarize(submission)}\n\n{FIELD_QUESTIONS[missing[0]]}"
            )
        if extraction.confirms:
            return self._submit(submission)
        return (
            "Voici le récapitulatif de votre annonce :\n"
            f"{summarize(submission)}\n\n"
            "Vous pouvez ajouter des photos (salon, chambre, cuisine, salle de bain, façade) "
            "avec le bouton « Ajouter une photo ». Répondez « oui » pour l'envoyer à la "
            "validation, ou corrigez une information."
        )

    def _submit(self, submission: ListingSubmission) -> str:
        submission.title = submission.title or default_title(submission)
        submission.status = "pending"
        submission.submitted_at = self.now()
        return (
            "Merci ! Votre annonce est envoyée. Un administrateur va la vérifier avant qu'elle "
            "soit visible des personnes qui cherchent un logement. Rien n'est publié avant cette validation."
        )

    def to_read(self, submission: ListingSubmission) -> SubmissionRead:
        return SubmissionRead(
            id=submission.id,
            status=submission.status,
            fields=fields_of(submission),
            missing_fields=missing_fields(submission),
            images=self.image_service.submission_images(submission.id),
            review_note=submission.review_note,
            created_at=submission.created_at or self.now(),
            submitted_at=submission.submitted_at,
            reviewed_at=submission.reviewed_at,
            approved_property_id=submission.approved_property_id,
        )

    def get_for_session(self, submission_id: int, session_id: str) -> ListingSubmission:
        """Une proposition n'est accessible qu'à la conversation qui l'a créée."""
        submission = self.repository.get(submission_id)
        if submission is None or submission.session_id != session_id:
            raise SubmissionNotFoundError()
        return submission

    @property
    def max_photo_bytes(self) -> int:
        return self.image_service.store.max_bytes

    def add_photo(self, submission_id: int, session_id: str, image_bytes: bytes, room: str) -> ImageRead:
        submission = self.get_for_session(submission_id, session_id)
        if submission.status not in ("draft", "pending"):
            raise SubmissionStateError()
        return self.image_service.add_owner_photo(submission.id, image_bytes, room)

    # --- Côté administrateur ------------------------------------------------------------

    def list_by_status(self, status: str) -> list[SubmissionRead]:
        return [self.to_read(item) for item in self.repository.by_status(status)]

    def approve(self, submission_id: int, note: str | None) -> SubmissionRead:
        submission = self._pending(submission_id)
        listing = self.repository.add_property(
            Property(
                source_id=self.repository.user_source().id,
                source_property_id=f"submission-{submission.id}",
                title=submission.title or default_title(submission),
                description=submission.description,
                city=submission.city,
                neighborhood=submission.neighborhood,
                property_type=submission.property_type,
                monthly_rent=submission.monthly_rent,
                bedrooms=submission.bedrooms,
                bathrooms=submission.bathrooms,
                furnished=submission.furnished,
                water_available=submission.water_available,
                electricity_available=submission.electricity_available,
                location_description=submission.location_description,
                contact_information=submission.contact_information,
                # Approuvée par un administrateur ne veut pas dire vérifiée sur place.
                listing_status="unconfirmed",
                verification_status="unverified",
                last_seen_at=self.now(),
            )
        )
        self.image_repository.attach_submission_to_property(submission.id, listing.id)
        submission.status = "approved"
        submission.approved_property_id = listing.id
        return self._review(submission, note)

    def reject(self, submission_id: int, note: str | None) -> SubmissionRead:
        submission = self._pending(submission_id)
        submission.status = "rejected"
        return self._review(submission, note)

    def _pending(self, submission_id: int) -> ListingSubmission:
        submission = self.repository.get_for_review(submission_id)
        if submission is None:
            raise SubmissionNotFoundError()
        if submission.status != "pending":
            raise SubmissionStateError("Seule une proposition en attente peut être approuvée ou refusée.")
        missing = missing_fields(submission)
        if missing:
            raise SubmissionStateError(f"Proposition incomplète : {', '.join(missing)}.")
        return submission

    def _review(self, submission: ListingSubmission, note: str | None) -> SubmissionRead:
        submission.review_note = note
        submission.reviewed_at = self.now()
        self.repository.commit()
        return self.to_read(submission)
