"""État des intégrations du hackathon : configuration et, sur demande, test réel."""

from typing import Literal

from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import KwatsurError
from app.integrations.data.zetaris import TABLE_NAME_PATTERN, ZetarisClient
from app.integrations.llm.openai_compatible import ChatCompletionClient

CheckStatus = Literal["not_configured", "configured", "ok", "error", "disabled"]


class IntegrationStatus(BaseModel):
    name: str
    status: CheckStatus
    detail: str


class IntegrationStatusService:
    def __init__(
        self,
        settings: Settings,
        zetaris_client: ZetarisClient,
        chat_client: ChatCompletionClient | None,
    ) -> None:
        self.settings = settings
        self.zetaris_client = zetaris_client
        self.chat_client = chat_client

    def report(self, live: bool) -> list[IntegrationStatus]:
        return [self._zetaris_status(live), self._llm_status(live)]

    def _zetaris_status(self, live: bool) -> IntegrationStatus:
        table = self.settings.zetaris_listings_table
        if not self.zetaris_client.is_configured or not table:
            return IntegrationStatus(
                name="zetaris",
                status="not_configured",
                detail="Renseigner ZETARIS_BASE_URL, ZETARIS_API_KEY, ZETARIS_ORG_ID et ZETARIS_LISTINGS_TABLE.",
            )
        mode = "active" if self.settings.listing_source == "zetaris" else "inactive (LISTING_SOURCE=postgres)"
        if not live:
            return IntegrationStatus(name="zetaris", status="configured", detail=f"Source {mode}.")
        try:
            # Même garde que ZetarisListingSource : le nom de table est injecté dans le SQL.
            if not TABLE_NAME_PATTERN.fullmatch(table):
                raise KwatsurError("ZETARIS_LISTINGS_TABLE est invalide.")
            rows = self.zetaris_client.run_query(f"SELECT id FROM {table}", max_rows=1)
        except KwatsurError as error:
            return IntegrationStatus(name="zetaris", status="error", detail=error.public_message)
        return IntegrationStatus(
            name="zetaris",
            status="ok",
            detail=f"Requête SQL réussie sur {table} ({len(rows)} ligne lue). Source {mode}.",
        )

    def _llm_status(self, live: bool) -> IntegrationStatus:
        name = self.settings.llm_provider
        if self.chat_client is None:
            return IntegrationStatus(name="llm", status="disabled", detail="LLM_PROVIDER=none.")
        if not self.chat_client.is_configured:
            key_name = "METERLESS_API_KEY" if name == "meterless" else "NEMOTRON_API_KEY"
            return IntegrationStatus(
                name=name, status="not_configured", detail=f"Renseigner {key_name}."
            )
        label = f"{self.chat_client.provider_label} — modèle {self.chat_client.model}"
        if not live:
            return IntegrationStatus(name=name, status="configured", detail=label)
        try:
            answer = self.chat_client.complete(
                [{"role": "user", "content": "Réponds uniquement par le mot OK."}],
                temperature=0.0,
                max_tokens=512,
            )
        except KwatsurError as error:
            return IntegrationStatus(name=name, status="error", detail=error.public_message)
        return IntegrationStatus(
            name=name, status="ok", detail=f"{label} a répondu ({len(answer)} caractères)."
        )
