from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment / .env file.

    Fields for later tasks (DB, JWT, SMTP, storage, seed user) are declared with
    safe defaults so the app boots without a populated .env during scaffolding.
    """

    app_name: str = "Legal Clinic Leads API"

    # Database (Task 2+)
    database_url: str = "postgresql+psycopg://legal:legal@localhost:5432/legal"

    # Auth / JWT (Task 8+)
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60

    # Email / SMTP -> Mailpit (Task 7+)
    smtp_host: str = "localhost"
    smtp_port: int = 1025

    # Local file storage (Task 6+)
    uploads_dir: str = "./uploads"

    # Seed attorney user (Task 4+)
    seed_attorney_email: str = "attorney@example.com"
    seed_attorney_password: str = "change-me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
