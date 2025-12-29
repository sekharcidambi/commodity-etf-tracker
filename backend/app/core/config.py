"""Application configuration"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Commodity ETF Tracker"
    VERSION: str = "0.1.0"

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/commodity_tracker",
        env="DATABASE_URL"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )

    # API Keys (External Data Sources)
    TWELVE_DATA_API_KEY: str = Field(default="", env="TWELVE_DATA_API_KEY")
    POLYGON_API_KEY: str = Field(default="", env="POLYGON_API_KEY")
    ALPHA_VANTAGE_API_KEY: str = Field(default="", env="ALPHA_VANTAGE_API_KEY")
    FRED_API_KEY: str = Field(default="", env="FRED_API_KEY")
    REDDIT_CLIENT_ID: str = Field(default="", env="REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: str = Field(default="", env="REDDIT_CLIENT_SECRET")

    # Data Collection
    ENABLE_SCHEDULER: bool = Field(default=True, env="ENABLE_SCHEDULER")
    DATA_COLLECTION_ENABLED: bool = Field(default=True, env="DATA_COLLECTION_ENABLED")

    # Tickers to track
    PRIMARY_TICKERS: List[str] = Field(
        default=["AGQ", "UGL"],
        env="PRIMARY_TICKERS"
    )
    EXTENDED_TICKERS: List[str] = Field(
        default=["ZSL", "GLD", "SLV", "PPLT"],
        env="EXTENDED_TICKERS"
    )

    # Futures symbols
    FUTURES_SYMBOLS: List[str] = Field(
        default=["GC=F", "SI=F", "PL=F"],  # Gold, Silver, Platinum futures
        env="FUTURES_SYMBOLS"
    )

    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Alert System
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: str = Field(default="", env="SMTP_USER")
    SMTP_PASSWORD: str = Field(default="", env="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str = Field(default="alerts@commodity-tracker.com", env="SMTP_FROM_EMAIL")
    SMTP_FROM_NAME: str = Field(default="Commodity ETF Tracker", env="SMTP_FROM_NAME")

    SLACK_WEBHOOK_URL: str = Field(default="", env="SLACK_WEBHOOK_URL")

    ALERT_COOLDOWN_MINUTES: int = Field(default=60, env="ALERT_COOLDOWN_MINUTES")
    ALERT_EXTREME_COOLDOWN_MINUTES: int = Field(default=1440, env="ALERT_EXTREME_COOLDOWN_MINUTES")  # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
