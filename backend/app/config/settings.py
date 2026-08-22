"""Application settings loaded from environment variables.

All secrets must be provided via environment variables (or a .env file in
local development). Nothing sensitive is hardcoded.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "Wiseweb-AI"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    frontend_url: str = "http://localhost:5173"

    # --- Database ---
    database_url: str = "postgresql+psycopg://wisewebai:wisewebai@localhost:5432/wisewebai"

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = False

    # --- Auth ---
    jwt_secret: str = Field(
        default="dev-only-change-me-in-production-1234",
        min_length=16,
        repr=False,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- AI ---
    ai_provider: str = "mock"  # openai | anthropic | mock
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_openai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: int = 60
    ai_max_context_chars: int = 24_000
    ai_enabled: bool = True

    # --- Crawler ---
    crawler_max_pages: int = 50
    crawler_max_depth: int = 3
    crawler_timeout: int = 15
    crawler_concurrency: int = 4
    crawler_delay: float = 0.25
    crawler_max_page_bytes: int = 5_242_880
    crawler_user_agent: str = (
        "WisewebAI-Bot/1.0 (+https://wiseweb-ai.local; passive website analysis)"
    )
    # Hard safety cap: never exceed this regardless of configuration.
    crawler_absolute_max_pages: int = 200
    crawler_absolute_max_depth: int = 5

    # Optional browser-based analysis (Playwright). Disabled by default.
    browser_enabled: bool = False
    axe_enabled: bool = False

    # --- Demo ---
    demo_user_email: str = "demo@wiseweb-ai.local"
    demo_user_password: str = "demopass123"
    seed_demo: bool = False
    # DEV-ONLY: allow the API to scan localhost/private targets (e.g. the
    # bundled demo site on http://localhost:8001). Relaxes SSRF protection;
    # never enable in production. Defaults to false.
    allow_localhost_scans: bool = False

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if v == "dev-only-change-me-in-production-1234":
            import warnings
            warnings.warn(
                "JWT_SECRET is set to the development default. "
                "Set a strong JWT_SECRET in production."
            )
        return v

    @field_validator("crawler_max_pages")
    @classmethod
    def cap_pages(cls, v: int) -> int:
        return min(v, 200)

    @field_validator("crawler_max_depth")
    @classmethod
    def cap_depth(cls, v: int) -> int:
        return min(v, 5)

    @property
    def crawler_delay_ms(self) -> float:
        return max(0.0, self.crawler_delay)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
