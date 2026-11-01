from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Universal Health QR API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://qr:qr_dev_password@localhost:5432/code"

    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:5174,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174"
    )

    jwt_secret: str = "change-me-in-production-m0-dev-only"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Dev auth stub (M0) — override via env in any shared/demo environment
    demo_username: str = "demo@health.local"
    demo_password: str = "demo-password-change-me"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
