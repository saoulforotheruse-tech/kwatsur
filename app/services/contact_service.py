"""Préparation d'un message de prise de contact. Rien n'est envoyé par Kwatsur."""

from app.schemas.property import ContactDraftResponse, PropertyRead
from app.services.ranking_service import format_fcfa
from app.services.risk_service import missing_information

SAFETY_NOTICE = (
    "Kwatsur n'envoie aucun message. Vérifiez l'annonce auprès de la source "
    "et ne versez jamais d'argent avant d'avoir visité le logement."
)


def build_contact_draft(listing: PropertyRead) -> ContactDraftResponse:
    location = ", ".join(filter(None, (listing.neighborhood, listing.city)))
    questions = ["Le logement est-il toujours disponible ?"]
    questions += [f"Pourriez-vous préciser : {label.lower()} ?" for label in missing_information(listing)[:3]]

    message = "\n".join(
        [
            "Bonjour,",
            "",
            f"Je suis intéressé(e) par votre annonce « {listing.title} » ({location}), "
            f"proposée à {format_fcfa(listing.monthly_rent)} par mois.",
            *questions,
            "Serait-il possible d'organiser une visite ?",
            "",
            "Merci d'avance pour votre réponse.",
        ]
    )

    notice = SAFETY_NOTICE
    if listing.source_is_demo:
        notice = "Annonce fictive de démonstration : aucun contact réel n'existe. " + SAFETY_NOTICE
    elif not listing.contact_information:
        notice = "La source ne fournit pas de coordonnées : passez par le lien de l'annonce. " + SAFETY_NOTICE

    return ContactDraftResponse(
        property_id=listing.id,
        message=message,
        contact_information=listing.contact_information,
        source_url=listing.source_url,
        notice=notice,
    )
