"""Contrat commun des fournisseurs de génération d'images.

Toute la logique de Kwatsur dépend de `ImageGenerationProvider`, jamais d'un fournisseur
précis. Pour en ajouter un (Hugging Face, modèle local…) :
1. créer un module voisin avec une classe qui respecte ce contrat (`name`, `model`,
   `is_configured`, `generate_image`) ;
2. convertir ses erreurs en erreurs ci-dessous ;
3. l'enregistrer dans `factory.py` sous un nom, puis mettre ce nom dans IMAGE_GENERATION_PROVIDER.
Aucune route, aucun service métier, ni le stockage n'ont à changer.
"""

from dataclasses import dataclass
from typing import Protocol

from app.core.exceptions import KwatsurError


@dataclass(frozen=True)
class GeneratedImage:
    """Résultat normalisé, identique quel que soit le fournisseur."""

    data: bytes
    content_type: str
    provider: str
    model: str


class ImageGenerationProvider(Protocol):
    name: str
    model: str

    @property
    def is_configured(self) -> bool: ...

    def generate_image(self, prompt: str) -> GeneratedImage:
        """Génère une image à partir d'une description ; lève une des erreurs communes en cas d'échec."""
        ...


# --- Erreurs communes : seules ces erreurs sortent d'un fournisseur ---------------------

class ImageGenerationNotConfiguredError(KwatsurError):
    status_code = 503
    public_message = "La génération d'images n'est pas configurée sur ce serveur."


class ImageProviderAuthenticationError(KwatsurError):
    status_code = 503
    public_message = (
        "Le fournisseur d'images a refusé les identifiants (jeton invalide, permissions "
        "insuffisantes ou identifiant de compte incorrect)."
    )


class ImageProviderQuotaError(KwatsurError):
    status_code = 429
    public_message = (
        "La limite du fournisseur d'images est atteinte (quota gratuit ou débit). "
        "Réessayez après son renouvellement."
    )


class ImageProviderUnavailableError(KwatsurError):
    status_code = 503
    public_message = "Le fournisseur d'images est momentanément indisponible. Réessayez plus tard."


class InvalidGeneratedImageError(KwatsurError):
    status_code = 502
    public_message = "Le fournisseur d'images a renvoyé une réponse inexploitable."


class UnknownImageProviderError(KwatsurError):
    status_code = 500
    public_message = "Le fournisseur d'images configuré (IMAGE_GENERATION_PROVIDER) est inconnu."


class DisabledImageProvider:
    """Utilisé quand IMAGE_GENERATION_ENABLED=false : l'application reste utilisable."""

    name = "disabled"
    model = "none"

    @property
    def is_configured(self) -> bool:
        return False

    def generate_image(self, prompt: str) -> GeneratedImage:
        raise ImageGenerationNotConfiguredError(
            "La génération d'images est désactivée (IMAGE_GENERATION_ENABLED=false)."
        )
