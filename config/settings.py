"""
Configuration management for Sea Street Detailing Meta Ads Agent.
Uses Pydantic for settings validation.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Meta API Credentials
    meta_access_token: str = Field(..., description="Meta API access token")
    meta_ad_account_id: str = Field(..., description="Ad account ID (format: act_XXXXX)")
    meta_app_id: str = Field(default="", description="Meta App ID (optional)")
    meta_app_secret: str = Field(default="", description="Meta App Secret (optional)")

    # Anthropic API
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")

    # Database
    database_path: Path = Field(
        default=Path("./data/sea_street.db"),
        description="Path to SQLite database"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_dir: Path = Field(default=Path("./data/logs"), description="Log directory")

    # Reports
    report_output_dir: Path = Field(
        default=Path("./data/exports"),
        description="Report output directory"
    )

    # Email (for daily reports)
    email_to: str = Field(default="", description="Email address to send reports to")
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username (usually your email)")
    smtp_password: str = Field(default="", description="SMTP password or app password")

    # Feature Flags
    enable_auto_actions: bool = Field(
        default=False,
        description="Enable automatic actions (pause ads, reduce budget)"
    )
    dry_run_mode: bool = Field(
        default=True,
        description="Simulate actions without making actual API calls"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    """Get application settings. Raises ValidationError if required fields are missing."""
    return Settings()
