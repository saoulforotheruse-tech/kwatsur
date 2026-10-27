"""Routes des propositions d'annonce : consultation et photos du propriétaire, validation admin."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import SubmissionServiceDependency, require_admin
from app.core.exceptions import KwatsurError
from app.schemas.image import ImageRead, RoomType
from app.schemas.submission import SubmissionRead, SubmissionReview, SubmissionStatus

router = APIRouter(prefix="/api", tags=["propositions d'annonce"])

# L'identifiant de conversation (UUID aléatoire) prouve que l'on est l'auteur de la proposition.
ConversationHeader = Annotated[str, Header(alias="X-Conversation-Id", min_length=1, max_length=36)]


class UploadTooLargeError(KwatsurError):
    status_code = 413
    public_message = "La photo dépasse la taille maximale autorisée."


@router.get("/submissions/{submission_id}", response_model=SubmissionRead, summary="Ma proposition d'annonce")
def read_submission(
    submission_id: int, conversation_id: ConversationHeader, submissions: SubmissionServiceDependency
) -> SubmissionRead:
    return submissions.to_read(submissions.get_for_session(submission_id, conversation_id))


@router.post(
    "/submissions/{submission_id}/photos",
    response_model=ImageRead,
    summary="Ajouter une photo réelle (corps : image JPEG, PNG ou WebP brute)",
)
async def upload_photo(
    submission_id: int,
    request: Request,
    conversation_id: ConversationHeader,
    submissions: SubmissionServiceDependency,
    room: Annotated[RoomType, Query()] = "autre",
) -> ImageRead:
    # Lecture bornée : on s'arrête dès que la limite est dépassée (pas de dépendance multipart).
    max_bytes = submissions.max_photo_bytes
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_bytes:
            raise UploadTooLargeError(f"La photo dépasse {max_bytes // 1_000_000} Mo.")
    # Écriture du fichier et de la base hors de la boucle asynchrone.
    return await run_in_threadpool(submissions.add_photo, submission_id, conversation_id, bytes(body), room)


@router.get(
    "/admin/submissions",
    response_model=list[SubmissionRead],
    dependencies=[Depends(require_admin)],
    summary="Propositions à valider (administrateur)",
)
def list_submissions(
    submissions: SubmissionServiceDependency, status: SubmissionStatus = "pending"
) -> list[SubmissionRead]:
    return submissions.list_by_status(status)


@router.post(
    "/admin/submissions/{submission_id}/approve",
    response_model=SubmissionRead,
    dependencies=[Depends(require_admin)],
    summary="Approuver : l'annonce devient visible des chercheurs",
)
def approve_submission(
    submission_id: int, review: SubmissionReview, submissions: SubmissionServiceDependency
) -> SubmissionRead:
    return submissions.approve(submission_id, review.note)


@router.post(
    "/admin/submissions/{submission_id}/reject",
    response_model=SubmissionRead,
    dependencies=[Depends(require_admin)],
    summary="Refuser la proposition",
)
def reject_submission(
    submission_id: int, review: SubmissionReview, submissions: SubmissionServiceDependency
) -> SubmissionRead:
    return submissions.reject(submission_id, review.note)
