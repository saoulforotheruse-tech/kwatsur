"""Contrat commun des fournisseurs de description d'image (vision : image → texte).

Sert à enrichir une illustration IA avec ce que montrent les VRAIES photos du propriétaire
(couleurs, matériaux, style). Un générateur texte → image comme FLUX.1 schnell ne lit pas
d'image : la photo passe donc par une description en texte.
Comme pour la génération, la logique de Kwatsur ne dépend que de ce contrat.
"""

from typing import Protocol

from app.integrations.image_generation.base import ImageGenerationNotConfiguredError


class ImageDescriber(Protocol):
    name: str
    model: str

    @property
    def is_configured(self) -> bool: ...

    def describe(self, image_bytes: bytes, question: str) -> str:
        """Décrit l'image en texte ; lève une erreur commune de `image_generation.base` en cas d'échec."""
        ...


class DisabledImageDescriber:
    """Utilisé quand IMAGE_DESCRIPTION_ENABLED=false : les illustrations se font sans les photos."""

    name = "disabled"
    model = "none"

    @property
    def is_configured(self) -> bool:
        return False

    def describe(self, image_bytes: bytes, question: str) -> str:
        raise ImageGenerationNotConfiguredError("La description des photos est désactivée.")
