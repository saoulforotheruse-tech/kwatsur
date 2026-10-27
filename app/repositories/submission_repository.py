"""Requêtes de persistance des annonces proposées."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.property import Property, PropertySource
from app.models.submission import ListingSubmission

USER_SOURCE_NAME = "Annonces proposées par les propriétaires"


class SubmissionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, submission_id: int) -> ListingSubmission | None:
        return self.session.get(ListingSubmission, submission_id)

    def get_for_review(self, submission_id: int) -> ListingSubmission | None:
        return self.session.scalar(
            select(ListingSubmission)
            .where(ListingSubmission.id == submission_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def open_draft(self, session_id: str) -> ListingSubmission | None:
        """Proposition en cours de description pour cette conversation, s'il y en a une."""
        statement = (
            select(ListingSubmission)
            .where(ListingSubmission.session_id == session_id, ListingSubmission.status == "draft")
            .order_by(ListingSubmission.id.desc())
        )
        return self.session.scalars(statement).first()

    def latest_for_session(self, session_id: str) -> ListingSubmission | None:
        statement = (
            select(ListingSubmission)
            .where(ListingSubmission.session_id == session_id)
            .order_by(ListingSubmission.id.desc())
        )
        return self.session.scalars(statement).first()

    def by_status(self, status: str) -> list[ListingSubmission]:
        statement = (
            select(ListingSubmission)
            .where(ListingSubmission.status == status)
            .order_by(ListingSubmission.submitted_at, ListingSubmission.id)
        )
        return list(self.session.scalars(statement))

    def add(self, submission: ListingSubmission) -> ListingSubmission:
        self.session.add(submission)
        self.session.flush()
        return submission

    def user_source(self) -> PropertySource:
        """Source des annonces approuvées : réelles (is_demo = false), jamais vérifiées d'office."""
        source = self.session.scalar(select(PropertySource).where(PropertySource.name == USER_SOURCE_NAME))
        if source is None:
            source = PropertySource(name=USER_SOURCE_NAME, source_type="user_submission", is_demo=False)
            self.session.add(source)
            self.session.flush()
        return source

    def add_property(self, listing: Property) -> Property:
        self.session.add(listing)
        self.session.flush()
        return listing

    def commit(self) -> None:
        self.session.commit()
