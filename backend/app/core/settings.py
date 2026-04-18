from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────
    APP_NAME: str = "Treeni AI Sustainability Platform"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-change-in-production"
    ENCRYPTION_KEY: str = ""

    # ── Database ─────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://treeni:treeni_secret@localhost:5432/treeni_ai"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── LLM ──────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.3
    EMBEDDING_MODEL: str = "text-embedding-004"

    # ── Contact Sourcing ─────────────────────────────
    APOLLO_API_KEY: str = ""
    HUNTER_API_KEY: str = ""
    ZEROBOUNCE_API_KEY: str = ""

    # ── Email ────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "sustainability@treeni.com"
    SENDGRID_FROM_NAME: str = "Treeni Sustainability"

    # ── ESG Sources ──────────────────────────────────
    RESUSTAIN_API_BASE: str = "https://api.resustain.com/v2"
    RESUSTAIN_API_KEY: str = ""
    CDP_API_KEY: str = ""
    SERPAPI_KEY: str = ""

    # ── Social Channels ──────────────────────────────
    LINKEDIN_ACCESS_TOKEN: str = ""
    WHATSAPP_API_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    # ── Feature Flags ────────────────────────────────
    USE_MOCK_ESG_DATA: bool = False
    HITL_CONFIDENCE_THRESHOLD: float = 0.75
    TIER3_HITL_THRESHOLD: float = 0.58

    # ── Worker ───────────────────────────────────────
    WORKER_CONCURRENCY: int = 10
    HTTP_TIMEOUT: int = 20

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def all_keys_configured(self) -> dict:
        return {
            "gemini":     bool(self.GEMINI_API_KEY),
            "apollo":     bool(self.APOLLO_API_KEY),
            "hunter":     bool(self.HUNTER_API_KEY),
            "zerobounce": bool(self.ZEROBOUNCE_API_KEY),
            "sendgrid":   bool(self.SENDGRID_API_KEY),
        }

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
