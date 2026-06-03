"""
Application configuration via Pydantic BaseSettings.

All settings are loaded from environment variables or a .env file.
Grouped by subsystem for clarity and maintainability.
"""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve project root (backend/ directory)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central configuration for the AgriIoT Security Framework."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "AgriIoT Security Framework"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_str: str = "/api/v1"

    # ── PostgreSQL ───────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "agri_iot_security"
    postgres_user: str = "agri_user"
    postgres_password: str = "agri_secure_password_change_me"
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/agri_iot.db"

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT Authentication ───────────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE_ME_TO_A_64_CHAR_HEX_STRING_FOR_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── Key Vault ────────────────────────────────────────────────────────────
    vault_master_secret: str = "CHANGE_ME_TO_A_64_CHAR_HEX_STRING_FOR_PRODUCTION"
    key_vault_dir: Path = BASE_DIR / "key_vault"

    # ── Security Gateway ─────────────────────────────────────────────────────
    nonce_expiry_seconds: int = 300
    timestamp_max_drift_seconds: int = 300

    # ── Rate Limiting ────────────────────────────────────────────────────────
    rate_limit_device_max: int = 60
    rate_limit_device_window: int = 60
    rate_limit_user_max: int = 120
    rate_limit_user_window: int = 60
    rate_limit_ip_max: int = 30
    rate_limit_ip_window: int = 60

    # ── Feature Drift ────────────────────────────────────────────────────────
    drift_window_size: int = 500
    drift_psi_threshold: float = 0.25
    drift_ks_alpha: float = 0.05

    # ── Trust Score ──────────────────────────────────────────────────────────
    trust_score_initial: float = 100.0
    trust_score_min: float = 0.0
    trust_score_max: float = 100.0
    trust_suspend_threshold: float = 50.0
    trust_block_threshold: float = 20.0

    # ── ML Models ────────────────────────────────────────────────────────────
    ml_models_dir: Path = BASE_DIR / "app" / "ml" / "models"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
