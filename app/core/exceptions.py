"""Exceptions applicatives et gestion des erreurs."""


class KwatsurError(Exception):
    """Erreur métier dont le message peut être montré à l'utilisateur."""

    status_code = 500
    public_message = "Une erreur interne est survenue."

    def __init__(self, public_message: str | None = None) -> None:
        super().__init__(public_message or self.public_message)
        if public_message:
            self.public_message = public_message


class IntegrationNotConfiguredError(KwatsurError):
    status_code = 503
    public_message = "Ce service externe n'est pas configuré."


class IntegrationUnavailableError(KwatsurError):
    status_code = 503
    public_message = "Un service externe est momentanément indisponible."


class InvalidIntegrationResponseError(KwatsurError):
    status_code = 502
    public_message = "Un service externe a renvoyé une réponse inexploitable."


class ConversationNotFoundError(KwatsurError):
    status_code = 404
    public_message = "Conversation introuvable."


class RateLimitExceededError(KwatsurError):
    status_code = 429
    public_message = "Trop de messages envoyés. Patientez une minute avant de réessayer."
