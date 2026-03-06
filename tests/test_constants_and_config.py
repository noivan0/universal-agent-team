"""Tests for constants and configuration modules.

Validates:
- Constants are properly defined and accessible
- Configuration validation works correctly
- Cross-field validation catches errors
- Default values are sensible
"""

import pytest
from config.constants import (
    MAX_AGENT_RETRIES,
    AGENT_TIMEOUT_SECONDS,
    COMPLEXITY_SCORE_THRESHOLDS,
    get_complexity_category,
    validate_retry_configuration,
    API_COMPRESSION_MIN_SIZE,
    API_COMPRESSION_LEVEL,
    ARTIFACT_AGENT_RELEVANCE,
    PATTERN_MIN_DATA_POINTS,
    ANOMALY_ZSCORE_THRESHOLD,
)
from backend.core.config import (
    Settings,
    DatabaseConfig,
    RedisConfig,
    AgentConfig,
)


class TestConstants:
    """Test constants module."""

    def test_max_retries_is_valid(self):
        """Agent retries should be reasonable."""
        assert 1 <= MAX_AGENT_RETRIES <= 10

    def test_agent_timeout_is_valid(self):
        """Agent timeout should be reasonable."""
        assert 30 <= AGENT_TIMEOUT_SECONDS <= 3600

    def test_complexity_thresholds_are_valid(self):
        """Complexity thresholds should be properly ordered."""
        assert len(COMPLEXITY_SCORE_THRESHOLDS) == 3

        for category, (min_score, max_score) in COMPLEXITY_SCORE_THRESHOLDS.items():
            assert min_score < max_score
            assert min_score >= 1
            assert max_score <= 100

    def test_compression_settings_valid(self):
        """Compression settings should be reasonable."""
        assert API_COMPRESSION_MIN_SIZE > 0
        assert 1 <= API_COMPRESSION_LEVEL <= 9

    def test_artifact_relevance_matrix_complete(self):
        """Artifact relevance should cover main agent types."""
        agents = {"frontend", "backend", "qa", "documentation"}

        for artifact_type, agent_scores in ARTIFACT_AGENT_RELEVANCE.items():
            # Check all agents covered
            assert set(agent_scores.keys()) == agents

            # Check scores are normalized 0-1
            for agent, score in agent_scores.items():
                assert 0.0 <= score <= 1.0

    def test_pattern_detection_constants_valid(self):
        """Pattern detection constants should be sensible."""
        assert PATTERN_MIN_DATA_POINTS > 0
        assert ANOMALY_ZSCORE_THRESHOLD > 0


class TestComplexityCalculation:
    """Test complexity scoring functions."""

    def test_get_complexity_category_valid_scores(self):
        """Should correctly categorize scores."""
        assert get_complexity_category(1) == "low"
        assert get_complexity_category(30) == "low"
        assert get_complexity_category(31) == "medium"
        assert get_complexity_category(60) == "medium"
        assert get_complexity_category(61) == "high"
        assert get_complexity_category(100) == "high"

    def test_get_complexity_category_invalid_scores(self):
        """Should raise error for invalid scores."""
        with pytest.raises(ValueError):
            get_complexity_category(0)

        with pytest.raises(ValueError):
            get_complexity_category(101)

        with pytest.raises(ValueError):
            get_complexity_category(-1)


class TestRetryValidation:
    """Test retry configuration validation."""

    def test_valid_configuration(self):
        """Valid configurations should pass."""
        assert validate_retry_configuration(3, 300) is True
        assert validate_retry_configuration(1, 30) is True
        assert validate_retry_configuration(10, 3600) is True

    def test_invalid_max_retries(self):
        """Should reject invalid retry counts."""
        with pytest.raises(ValueError, match="max_retries must be at least 1"):
            validate_retry_configuration(0, 300)

    def test_invalid_timeout_too_small(self):
        """Should reject timeout below minimum."""
        with pytest.raises(ValueError, match="at least 30 seconds"):
            validate_retry_configuration(3, 29)

    def test_invalid_timeout_too_large(self):
        """Should reject timeout above maximum."""
        with pytest.raises(ValueError, match="must not exceed 3600 seconds"):
            validate_retry_configuration(3, 3601)


class TestDatabaseConfig:
    """Test database configuration validation."""

    def test_valid_postgresql_url(self):
        """Should accept PostgreSQL URLs."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        assert config.url == "postgresql://user:pass@localhost/db"

    def test_valid_postgres_url(self):
        """Should accept postgres:// scheme."""
        config = DatabaseConfig(url="postgres://user:pass@localhost/db")
        assert config.url == "postgres://user:pass@localhost/db"

    def test_valid_sqlite_url(self):
        """Should accept SQLite URLs."""
        config = DatabaseConfig(url="sqlite:///data.db")
        assert config.url == "sqlite:///data.db"

    def test_invalid_database_url(self):
        """Should reject invalid URLs."""
        with pytest.raises(ValueError, match="Database URL must start with"):
            DatabaseConfig(url="invalid://localhost/db")

    def test_pool_size_validation(self):
        """Should validate pool size bounds."""
        # Valid
        config = DatabaseConfig(pool_size=20)
        assert config.pool_size == 20

        # Too small
        with pytest.raises(ValueError):
            DatabaseConfig(pool_size=2)

        # Too large
        with pytest.raises(ValueError):
            DatabaseConfig(pool_size=101)

    def test_pool_timeout_validation(self):
        """Should validate pool timeout."""
        # Valid
        config = DatabaseConfig(pool_timeout=30)
        assert config.pool_timeout == 30

        # Too small
        with pytest.raises(ValueError):
            DatabaseConfig(pool_timeout=0)

        # Too large
        with pytest.raises(ValueError):
            DatabaseConfig(pool_timeout=301)


class TestRedisConfig:
    """Test Redis configuration validation."""

    def test_valid_redis_url(self):
        """Should accept valid Redis URLs."""
        config = RedisConfig(url="redis://localhost:6379")
        assert config.url == "redis://localhost:6379"

    def test_invalid_redis_url(self):
        """Should reject invalid Redis URLs."""
        with pytest.raises(ValueError, match="Redis URL must start with"):
            RedisConfig(url="memcached://localhost:6379")

    def test_pool_size_validation(self):
        """Should validate Redis pool size."""
        # Valid
        config = RedisConfig(pool_size=10)
        assert config.pool_size == 10

        # Too small
        with pytest.raises(ValueError):
            RedisConfig(pool_size=2)

        # Too large
        with pytest.raises(ValueError):
            RedisConfig(pool_size=51)

    def test_retry_attempts_validation(self):
        """Should validate retry attempts."""
        # Valid
        config = RedisConfig(retry_attempts=3)
        assert config.retry_attempts == 3

        # Too small
        with pytest.raises(ValueError):
            RedisConfig(retry_attempts=0)

        # Too large
        with pytest.raises(ValueError):
            RedisConfig(retry_attempts=11)


class TestAgentConfig:
    """Test agent configuration validation."""

    def test_valid_agent_config(self):
        """Should accept valid agent configuration."""
        config = AgentConfig(max_retries=3, timeout_seconds=300)
        assert config.max_retries == 3
        assert config.timeout_seconds == 300

    def test_max_retries_bounds(self):
        """Should validate max_retries."""
        # Valid
        config = AgentConfig(max_retries=5)
        assert config.max_retries == 5

        # Too small
        with pytest.raises(ValueError):
            AgentConfig(max_retries=0)

        # Too large
        with pytest.raises(ValueError):
            AgentConfig(max_retries=11)

    def test_timeout_bounds(self):
        """Should validate timeout."""
        # Valid
        config = AgentConfig(timeout_seconds=300)
        assert config.timeout_seconds == 300

        # Too small
        with pytest.raises(ValueError, match="at least 30"):
            AgentConfig(timeout_seconds=29)

        # Too large
        with pytest.raises(ValueError, match="must not exceed 3600"):
            AgentConfig(timeout_seconds=3601)


class TestSettingsValidation:
    """Test full settings configuration."""

    def test_settings_initialization(self):
        """Should initialize with defaults."""
        settings = Settings()
        assert settings.app_name == "Cycle Time Monitoring System"
        assert settings.debug is False
        assert settings.log_level == "INFO"

    def test_log_level_validation(self):
        """Should validate log level."""
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(log_level=level)
            assert settings.log_level == level

        # Invalid level
        with pytest.raises(ValueError):
            Settings(log_level="INVALID")

    def test_database_config_nested(self):
        """Should properly handle nested database config."""
        settings = Settings()
        assert settings.database.pool_size > 0
        assert settings.database.url is not None

    def test_redis_config_nested(self):
        """Should properly handle nested Redis config."""
        settings = Settings()
        assert settings.redis.pool_size > 0
        assert settings.redis.url is not None

    def test_agent_config_nested(self):
        """Should properly handle nested agent config."""
        settings = Settings()
        assert settings.agent.max_retries > 0
        assert settings.agent.timeout_seconds > 0

    def test_settings_dump(self):
        """Should be able to dump to dict."""
        settings = Settings()
        data = settings.model_dump()

        assert "database" in data
        assert "redis" in data
        assert "agent" in data
        assert data["app_name"] == "Cycle Time Monitoring System"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
