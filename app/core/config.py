"""Configuration de l'application chargée depuis l'environnement."""

from typing import Literal

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Kwatsur"
    database_url: str = "postgresql+psycopg://kwatsur:kwatsur_dev@localhost:5432/kwatsur"
    cors_origins: str = "http://localhost:8080"

    # Repli complet si Zetaris, Nightshift ou Cloudflare sont indisponibles (voir apply_sample_mode).
    sample_mode: bool = False

    # Source des annonces : « zetaris » interroge Zetaris, « postgres » lit la base locale.
    listing_source: Literal["postgres", "zetaris"] = "postgres"
    # Si Zetaris échoue, bascule vers PostgreSQL en le signalant dans la réponse.
    zetaris_fallback_to_postgres: bool = True

    # Zetaris : API REST de l'installation locale (ex. http://127.0.0.1:8888, org 1).
    zetaris_base_url: str = ""
    zetaris_api_key: str = ""
    zetaris_org_id: str = ""
    zetaris_listings_table: str = ""
    zetaris_timeout_seconds: float = 60.0

    # Fournisseur du modèle : Nemotron via Meterless, Nemotron en direct (catalogue NVIDIA),
    # « rules » (mode démo sans IA ni clé) ou « none » (chat désactivé).
    llm_provider: Literal["nemotron", "meterless", "rules", "none"] = "rules"
    llm_timeout_seconds: float = 60.0
    # Raisonnement caché de Nemotron : désactivé, la réponse arrive environ 4 fois plus vite.
    llm_thinking_enabled: bool = False

    nemotron_base_url: str = "https://integrate.api.nvidia.com/v1"
    nemotron_api_key: str = ""
    nemotron_model: str = "nvidia/nemotron-3.5-bolt-e4b"

    # Meterless Runtime : API compatible OpenAI exposée en local.
    meterless_base_url: str = "http://127.0.0.1:8088/v1"
    meterless_api_key: str = ""
    meterless_model: str = "meterless/auto"
    meterless_app_id: str = "kwatsur"

    # Meterless Scout Intent : secret HMAC des contrats d'exécution (éphémère s'il est vide).
    scout_signing_secret: str = ""

    # Nombre maximal de messages /api/chat par client et par minute.
    chat_rate_limit_per_minute: int = 20

    # Images : fichiers sur disque (volume Docker), métadonnées dans PostgreSQL.
    media_directory: str = "media"
    image_upload_max_bytes: int = 5_000_000

    # Génération d'images illustratives. Le fournisseur se choisit ici et nulle part ailleurs.
    image_generation_enabled: bool = True
    image_generation_provider: str = "cloudflare"
    # Limite propre à Kwatsur (images générées avec succès par jour UTC), distincte du quota
    # du fournisseur. Valeur prudente par défaut pour éviter les dépenses accidentelles.
    image_generation_daily_limit: int = 2
    image_generation_timeout_seconds: float = 60.0

    # Cloudflare Workers AI (https://developers.cloudflare.com/workers-ai/get-started/rest-api/).
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_image_model: str = "@cf/black-forest-labs/flux-1-schnell"
    # Étapes de diffusion de FLUX.1 schnell : 4 par défaut, 8 au maximum (schéma du modèle).
    cloudflare_image_steps: int = Field(default=4, ge=1, le=8)

    # Vision : décrire les vraies photos du propriétaire pour enrichir une illustration.
    image_description_enabled: bool = True
    cloudflare_vision_model: str = "@cf/llava-hf/llava-1.5-7b-hf"
    # Photos décrites au plus par illustration, et taille maximale envoyée (octets en JSON).
    vision_max_reference_photos: int = Field(default=2, ge=0, le=4)
    vision_max_photo_bytes: int = 1_500_000

    # Validation des annonces proposées : jeton à saisir sur /admin.html (vide = administration fermée).
    admin_token: str = ""

    @field_validator(
        "nemotron_base_url", "nemotron_model", "meterless_base_url", "meterless_model",
        "meterless_app_id", "image_generation_provider", "cloudflare_image_model", "cloudflare_vision_model", mode="before",
    )
    @classmethod
    def use_default_when_blank(cls, value: object, info: ValidationInfo) -> object:
        # Une variable présente mais vide dans .env ne doit pas effacer la valeur par défaut.
        if isinstance(value, str) and not value.strip():
            return cls.model_fields[info.field_name].default
        return value

    @model_validator(mode="after")
    def apply_sample_mode(self) -> "Settings":
        """SAMPLE_MODE=true : tout fonctionne sans Zetaris, Nightshift ni Cloudflare.

        Annonces fictives de PostgreSQL, critères compris par des règles, pas de génération
        d'images ; Scout Intent reste actif. Chaque réponse l'annonce (« Mode démo sans IA »).
        """
        if self.sample_mode:
            self.listing_source = "postgres"
            self.llm_provider = "rules"
            self.image_generation_enabled = False
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
