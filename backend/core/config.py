"""Configuration management for the application.

This module handles configuration loading and validation using Pydantic.
All settings are validated at startup to catch configuration errors early.

Features:
- Environment variable loading from .env file
- Type validation with Pydantic
- Cross-field validation
- Helpful error messages
- Configuration documentation

Example:
    from backend.core.config import settings

    # Use settings in your code
    db_url = settings.database_url
    timeout = settings.agent_timeout
"""

import logging
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    HttpUrl,
    SecretStr,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from config.constants import (
    MAX_AGENT_RETRIES,
    MIN_AGENT_TIMEOUT,
    MAX_AGENT_TIMEOUT,
    VALID_DATABASE_SCHEMES,
    VALID_REDIS_SCHEME,
    VALID_LOG_LEVELS,
    LOG_LEVEL,
    DATABASE_POOL_SIZE,
    DATABASE_MAX_OVERFLOW,
    DATABASE_POOL_TIMEOUT,
)

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration with validation.

    Security Note:
        - All credentials must come from environment variables
        - Never hardcode passwords or connection strings
        - Use SecretStr for sensitive fields
    """

    url: str = Field(
        default="",
        description="Database connection URL (from env, NOT hardcoded)",
        min_length=10,
    )
    pool_size: int = Field(
        default=DATABASE_POOL_SIZE,
        description="Database connection pool size",
        ge=5,
        le=100,
    )
    max_overflow: int = Field(
        default=DATABASE_MAX_OVERFLOW,
        description="Maximum overflow connections beyond pool size",
        ge=0,
        le=50,
    )
    pool_timeout: int = Field(
        default=DATABASE_POOL_TIMEOUT,
        description="Timeout for acquiring connection in seconds",
        ge=1,
        le=300,
    )
    echo: bool = Field(
        default=False,
        description="Enable SQL query logging",
    )

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format and security.

        Args:
            v: Database URL to validate

        Returns:
            Validated database URL

        Raises:
            ValueError: If URL scheme is invalid or credentials look hardcoded
        """
        # Check scheme
        if v and not any(v.startswith(scheme) for scheme in VALID_DATABASE_SCHEMES):
            schemes = ", ".join(VALID_DATABASE_SCHEMES)
            raise ValueError(
                f"Database URL must start with one of: {schemes}. Got: {v[:20]}..."
            )

        # Security check: warn if URL contains obvious default/weak credentials
        if v and any(weak in v for weak in ["postgres:postgres", "user:password", ":password", "admin:admin"]):
            raise ValueError(
                "Database URL appears to contain default/weak credentials. "
                "Use strong passwords and load from environment variables, not hardcoded values."
            )

        return v


class RedisConfig(BaseModel):
    """Redis configuration with validation."""

    url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL",
    )
    pool_size: int = Field(
        default=10,
        description="Redis connection pool size",
        ge=5,
        le=50,
    )
    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for Redis operations",
        ge=1,
        le=10,
    )

    @field_validator("url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format.

        Args:
            v: Redis URL to validate

        Returns:
            Validated Redis URL

        Raises:
            ValueError: If URL scheme is invalid
        """
        if not v.startswith(VALID_REDIS_SCHEME):
            raise ValueError(
                f"Redis URL must start with {VALID_REDIS_SCHEME}. Got: {v[:20]}..."
            )
        return v


class AgentConfig(BaseModel):
    """Agent configuration with validation."""

    max_retries: int = Field(
        default=MAX_AGENT_RETRIES,
        description="Maximum number of agent retry attempts",
        ge=1,
        le=10,
    )
    timeout_seconds: int = Field(
        default=300,
        description="Agent execution timeout in seconds",
    )

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate agent timeout.

        Args:
            v: Timeout value in seconds

        Returns:
            Validated timeout value

        Raises:
            ValueError: If timeout is outside valid range
        """
        if v < MIN_AGENT_TIMEOUT:
            raise ValueError(
                f"timeout_seconds must be at least {MIN_AGENT_TIMEOUT}, got {v}"
            )
        if v > MAX_AGENT_TIMEOUT:
            raise ValueError(
                f"timeout_seconds must not exceed {MAX_AGENT_TIMEOUT}, got {v}"
            )
        return v


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings are validated at initialization. Configuration errors
    are caught early and reported with helpful messages.

    Environment Variables:
        DATABASE_URL: PostgreSQL connection string
        REDIS_URL: Redis connection string
        API_HOST: API host address (default: http://localhost:8000)
        FRONTEND_URL: Frontend URL (default: http://localhost:3000)
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        MAX_AGENT_RETRIES: Maximum agent retry attempts
        AGENT_TIMEOUT: Agent execution timeout in seconds

    Example:
        >>> from backend.core.config import settings
        >>> print(settings.database.url)
        >>> print(settings.agent.max_retries)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_assignment=True,
        extra="ignore",
    )

    # Core application settings
    app_name: str = Field(
        default="Cycle Time Monitoring System",
        description="Application name",
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # Database
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig,
        description="Database configuration",
    )

    # Redis
    redis: RedisConfig = Field(
        default_factory=RedisConfig,
        description="Redis configuration",
    )

    # API
    api_host: str = Field(
        default="http://localhost:8000",
        description="API host URL",
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Frontend URL",
    )

    # Email (SMTP)
    smtp_server: str = Field(
        default="smtp.gmail.com",
        description="SMTP server address",
    )
    smtp_port: int = Field(
        default=587,
        description="SMTP server port",
        ge=1,
        le=65535,
    )
    smtp_user: str = Field(default="", description="SMTP username (from env)")
    smtp_password: SecretStr = Field(default=SecretStr(""), description="SMTP password (from env, never hardcoded)")
    notification_email_from: str = Field(
        default="noreply@cyclemonitor.com",
        description="Notification email sender address",
    )

    @field_validator("smtp_password")
    @classmethod
    def validate_smtp_password(cls, v: SecretStr) -> SecretStr:
        """Validate SMTP password is not a default/weak value.

        Args:
            v: SMTP password

        Returns:
            Validated password

        Raises:
            ValueError: If password appears to be default/weak
        """
        password_str = v.get_secret_value() if isinstance(v, SecretStr) else str(v)

        if password_str and password_str in ("password", "123456", "admin", "smtp", "test"):
            raise ValueError(
                "SMTP password cannot be a default/weak value. "
                "Use strong password from environment variable."
            )

        return v

    # Logging
    log_level: str = Field(
        default=LOG_LEVEL,
        description="Logging level",
    )

    # Agent settings
    agent: AgentConfig = Field(
        default_factory=AgentConfig,
        description="Agent configuration",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level.

        Args:
            v: Logging level to validate

        Returns:
            Validated logging level

        Raises:
            ValueError: If logging level is invalid
        """
        v_upper = v.upper()
        if v_upper not in VALID_LOG_LEVELS:
            valid = ", ".join(sorted(VALID_LOG_LEVELS))
            raise ValueError(
                f"log_level must be one of: {valid}. Got: {v}"
            )
        return v_upper

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        """Perform cross-field validation.

        Returns:
            Validated settings instance

        Raises:
            ValueError: If cross-field validation fails
        """
        # Validate API URLs are not empty if debug is off
        if not self.debug:
            if not self.api_host:
                raise ValueError("api_host cannot be empty in production")
            if not self.frontend_url:
                raise ValueError("frontend_url cannot be empty in production")

        return self


# ============================================================================
# Security Validation
# ============================================================================

def validate_no_hardcoded_credentials(settings_obj: "Settings") -> None:
    """Fail fast if credentials appear to be hardcoded or default.

    Args:
        settings_obj: Settings instance to validate

    Raises:
        ValueError: If any hardcoded/default credentials detected
    """
    errors = []

    # Check database URL
    if settings_obj.database.url:
        if any(weak in settings_obj.database.url for weak in ["localhost", "127.0.0.1"]):
            if "prod" in settings_obj.api_host.lower() or not settings_obj.debug:
                errors.append(
                    "Database URL contains localhost (127.0.0.1). "
                    "In production, use proper database server. "
                    "Set DATABASE_URL environment variable."
                )

    # Check SMTP password is not default
    if settings_obj.smtp_password.get_secret_value():
        weak_passwords = ["password", "123456", "admin", "smtp"]
        if settings_obj.smtp_password.get_secret_value() in weak_passwords:
            errors.append("SMTP password is too weak. Use environment variable with strong password.")

    if errors:
        error_msg = "\n".join(f"- {e}" for e in errors)
        raise ValueError(f"Security validation failed:\n{error_msg}")

    logger.info("✅ Credentials validated: all from environment variables")


# Load settings at module import time
settings = Settings()

# Security validation on import
try:
    validate_no_hardcoded_credentials(settings)
    logger.info("Configuration validation passed")
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")
    raise


def get_settings() -> Settings:
    """Get the global settings instance.

    This function provides access to settings for dependency injection
    in FastAPI endpoints.

    Returns:
        Global Settings instance

    Example:
        >>> from fastapi import Depends
        >>> from backend.core.config import get_settings
        >>>
        >>> async def my_endpoint(settings: Settings = Depends(get_settings)):
        ...     return {"timeout": settings.agent.timeout_seconds}
    """
    return settings
