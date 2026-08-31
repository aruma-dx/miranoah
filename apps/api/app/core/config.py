from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "MIRANOAH"
    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"

    database_url: str = "postgresql+psycopg://miranoah:miranoah@localhost:5432/miranoah"
    redis_url: str = "redis://localhost:6379/0"

    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""

    openai_api_key: str = ""
    openai_model_fast: str = "gpt-5-mini"
    openai_model_reasoning: str = "gpt-5.6"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    notion_token: str = ""

    session_secret: str = "change-me"
    jwt_secret: str = "change-me-too"
    raw_slack_retention_days: int = 180

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
