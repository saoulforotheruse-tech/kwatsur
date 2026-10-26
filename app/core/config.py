"""Configuration de l'application chargée depuis l'environnement."""

from typing import Literal

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Kwatsur"
    database_url: str = "postgresql+psycopg://kwatsur:kwatsur_dev@localhost:5432/kwatsur"
    cors_origins: str = "http://localhost:8080"

    # Source des annonces : « zetaris » interroge Zetaris, « postgres » lit la base locale.
    listing_source: Literal["postgres", "zetaris"] = "postgres"
    # Si Zetaris échoue, bascule vers PostgreSQL en le signalant dans la réponse.
    zetaris_fallback_to_postgres: bool = True

    # Zetaris : API REST officielle (https://api.saas.enterprise.zetaris.com/redoc).
    zetaris_base_url: str = ""
    zetaris_api_key: str = ""
    zetaris_org_id: str = ""
    zetaris_listings_table: str = ""
    zetaris_timeout_seconds: float = 20.0

    # Fournisseur du modèle : Nemotron en direct (catalogue NVIDIA) ou via Meterless.
    llm_provider: Literal["nemotron", "meterless", "none"] = "nemotron"
    llm_timeout_seconds: float = 60.0

    nemotron_base_url: str = "https://integrate.api.nvidia.com/v1"
    nemotron_api_key: str = ""
    nemotron_model: str = "nvidia/nemotron-3.5-bolt-e4b"

    # Meterless Runtime : API compatible OpenAI exposée en local.
    meterless_base_url: str = "http://127.0.0.1:8088/v1"
    meterless_api_key: str = ""
    meterless_model: str = "meterless/auto"
    meterless_app_id: str = "kwatsur"

    # Nombre maximal de messages /api/chat par client et par minute.
    chat_rate_limit_per_minute: int = 20

    @field_validator(
        "nemotron_base_url", "nemotron_model", "meterless_base_url", "meterless_model",
        "meterless_app_id", mode="before",
    )
    @classmethod
    def use_default_when_blank(cls, value: object, info: ValidationInfo) -> object:
        # Une variable présente mais vide dans .env ne doit pas effacer la valeur par défaut.
        if isinstance(value, str) and not value.strip():
            return cls.model_fields[info.field_name].default
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
