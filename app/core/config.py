"""Configuration de l'application chargée depuis l'environnement."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Kwatsur"
    database_url: str = "postgresql+psycopg://kwatsur:kwatsur_dev@localhost:5432/kwatsur"
    cors_origins: str = "http://localhost:8080"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
