"""Doublures de test (MOCKS) : elles ne communiquent avec aucun service réel."""

from collections.abc import Callable

from app.core.exceptions import KwatsurError
from app.integrations.llm.base import ChatTurn, ReplyContext
from app.schemas.chat import ReplyAuthor
from app.schemas.criteria import CriteriaExtraction, SearchCriteria
from app.schemas.submission import ListingExtraction, ListingFields

ExtractionRule = Callable[[str, SearchCriteria], CriteriaExtraction]


class MockLLMProvider:
    """Fournisseur IA simulé : extraction scriptée, réponse construite à partir du contexte."""

    name: ReplyAuthor = "nemotron"

    def __init__(
        self,
        extraction_rule: ExtractionRule,
        extraction_error: KwatsurError | None = None,
        reply_error: KwatsurError | None = None,
    ) -> None:
        self.extraction_rule = extraction_rule
        self.extraction_error = extraction_error
        self.reply_error = reply_error
        self.received_histories: list[list[ChatTurn]] = []
        # Extraction d'annonce scriptée (propriétaire) : vide par défaut.
        self.listing_rule: Callable[[str, ListingFields], ListingExtraction] = (
            lambda _message, _current: ListingExtraction()
        )
        self.received_contexts: list[ReplyContext] = []

    def extract_criteria(
        self, message: str, history: list[ChatTurn], current: SearchCriteria
    ) -> CriteriaExtraction:
        self.received_histories.append(history)
        if self.extraction_error:
            raise self.extraction_error
        return self.extraction_rule(message, current)

    def extract_listing(
        self, message: str, history: list[ChatTurn], current: ListingFields
    ) -> ListingExtraction:
        self.received_histories.append(history)
        return self.listing_rule(message, current)

    def write_reply(self, context: ReplyContext) -> str:
        self.received_contexts.append(context)
        if self.reply_error:
            raise self.reply_error
        return f"[réponse simulée] {context.total_results} résultat(s)."


def scripted_extractions(*extractions: dict) -> ExtractionRule:
    """Renvoie successivement les extractions fournies, une par message."""
    queue = [CriteriaExtraction.model_validate(item) for item in extractions]

    def rule(_message: str, _current: SearchCriteria) -> CriteriaExtraction:
        return queue.pop(0)

    return rule


# Plus petit PNG valide (1 × 1 pixel) : de vrais octets d'image, sans appel réseau.
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


class FakeImageProvider:
    """Fournisseur d'images simulé (MOCK) : renvoie une petite image PNG, sans réseau."""

    name = "fake"
    model = "fake-model"

    def __init__(self, configured: bool = True, error: KwatsurError | None = None) -> None:
        self.configured = configured
        self.error = error
        self.prompts: list[str] = []

    @property
    def is_configured(self) -> bool:
        return self.configured

    def generate_image(self, prompt: str):
        from app.integrations.image_generation.base import GeneratedImage, ImageGenerationNotConfiguredError

        if not self.configured:
            raise ImageGenerationNotConfiguredError()
        if self.error:
            raise self.error
        self.prompts.append(prompt)
        return GeneratedImage(data=TINY_PNG, content_type="image/png", provider=self.name, model=self.model)


class FakeImageDescriber:
    """Modèle de vision simulé (MOCK) : renvoie une description fixe, sans réseau."""

    name = "fake-vision"
    model = "fake-vision-model"

    def __init__(self, description: str = "Murs jaunes, sol carrelé blanc.") -> None:
        self.description = description
        self.received_sizes: list[int] = []

    @property
    def is_configured(self) -> bool:
        return True

    def describe(self, image_bytes: bytes, question: str) -> str:
        self.received_sizes.append(len(image_bytes))
        return self.description
