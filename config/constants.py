"""Centralized constants for the Universal Agent Team system.

This module contains all magic numbers and configuration constants used throughout
the application. By centralizing constants, we achieve:

1. Single source of truth for configuration values
2. Easier maintenance and updates
3. Clear documentation of configuration boundaries
4. Type safety with proper typing

Usage:
    from config.constants import MAX_AGENT_RETRIES, AGENT_TIMEOUT_SECONDS

    for attempt in range(MAX_AGENT_RETRIES):
        try:
            result = agent.execute(timeout=AGENT_TIMEOUT_SECONDS)
            break
        except TimeoutError:
            pass
"""

# ============================================================================
# Agent Configuration
# ============================================================================

MAX_AGENT_RETRIES: int = 3
"""Maximum number of retry attempts for agent execution."""

AGENT_TIMEOUT_SECONDS: int = 300
"""Maximum execution time for an agent in seconds (5 minutes)."""

EXPONENTIAL_BACKOFF_BASE: int = 2
"""Base for exponential backoff calculation (2^n seconds between retries)."""

MIN_AGENT_TIMEOUT: int = 30
"""Minimum allowed agent timeout in seconds."""

MAX_AGENT_TIMEOUT: int = 3600
"""Maximum allowed agent timeout in seconds (1 hour)."""


# ============================================================================
# Complexity Scoring Configuration
# ============================================================================

COMPLEXITY_BASE_SCORE: int = 50
"""Base score for complexity calculation."""

COMPLEXITY_MAX_SCORE: int = 100
"""Maximum allowed complexity score."""

COMPLEXITY_MIN_SCORE: int = 1
"""Minimum allowed complexity score."""

COMPLEXITY_SCORE_THRESHOLDS: dict[str, tuple[int, int]] = {
    "low": (1, 30),
    "medium": (31, 60),
    "high": (61, 100),
}
"""Complexity score range thresholds for classification."""

# Keyword multipliers for complexity factors
COMPLEXITY_FACTORS: dict[str, int] = {
    # Real-time features
    "real-time": 20,
    "live data": 20,
    "streaming": 20,
    "websocket": 20,

    # Scalability features
    "microservice": 25,
    "distributed": 25,
    "scalable": 15,
    "high-load": 20,

    # Security features
    "authentication": 10,
    "oauth": 15,
    "multi-tenant": 15,
    "encryption": 15,

    # Payment processing
    "payment": 15,
    "billing": 12,
    "subscription": 10,

    # Data processing
    "analytics": 15,
    "machine learning": 20,
    "big data": 20,
}
"""Complexity multipliers for various feature keywords."""


# ============================================================================
# Context Compaction Configuration
# ============================================================================

CONTEXT_RELEVANCE_THRESHOLD: float = 0.3
"""Minimum relevance score to include full details (0.0-1.0)."""

HIGH_RELEVANCE_THRESHOLD: float = 0.8
"""Threshold above which to include 100% of artifact details."""

MEDIUM_RELEVANCE_THRESHOLD: float = 0.5
"""Threshold for including ~50% of artifact details."""

LOW_RELEVANCE_THRESHOLD: float = 0.2
"""Threshold for including just metadata/summary."""

STATE_COMPRESSION_THRESHOLD: int = 100_000
"""Compress state when size exceeds this many bytes (100 KB)."""

CONTEXT_COMPRESSION_TARGET_SIZE: int = 4000
"""Target size for compressed context in tokens (approximately 16 KB)."""

# Relevance matrix: how relevant each artifact type is to each agent
ARTIFACT_AGENT_RELEVANCE: dict[str, dict[str, float]] = {
    # API specifications
    "api_specs": {
        "frontend": 1.0,
        "backend": 1.0,
        "qa": 0.9,
        "documentation": 0.8,
    },
    # Component specifications
    "component_specs": {
        "frontend": 1.0,
        "backend": 0.2,
        "qa": 0.4,
        "documentation": 0.6,
    },
    # Database schema
    "database_schema": {
        "frontend": 0.3,
        "backend": 1.0,
        "qa": 0.7,
        "documentation": 0.7,
    },
    # Architecture design
    "architecture_doc": {
        "frontend": 0.7,
        "backend": 0.8,
        "qa": 0.8,
        "documentation": 1.0,
    },
    # Design system
    "design_system": {
        "frontend": 1.0,
        "backend": 0.1,
        "qa": 0.2,
        "documentation": 0.5,
    },
    # Deployment guide
    "deployment_guide": {
        "frontend": 0.2,
        "backend": 0.4,
        "qa": 0.3,
        "documentation": 0.9,
    },
    # Frontend code
    "frontend_code": {
        "frontend": 1.0,
        "backend": 0.1,
        "qa": 0.6,
        "documentation": 0.4,
    },
    # Backend code
    "backend_code": {
        "frontend": 0.1,
        "backend": 1.0,
        "qa": 0.8,
        "documentation": 0.5,
    },
}
"""Relevance scores for artifact types to different agents."""


# ============================================================================
# State Management Configuration
# ============================================================================

CHECKPOINT_BATCH_SIZE: int = 100
"""Number of operations to batch before writing checkpoint."""

CHECKPOINT_RETENTION_DAYS: int = 30
"""Number of days to retain checkpoint files."""

MAX_STATE_SIZE_MB: int = 100
"""Maximum allowed state size in megabytes."""

STATE_VALIDATION_INTERVAL: int = 10
"""Validate state integrity every N operations."""


# ============================================================================
# Dependency Resolution Configuration
# ============================================================================

DEPENDENCY_CACHE_MAX_SIZE: int = 1000
"""Maximum number of dependency resolution results to cache."""

DEPENDENCY_RESOLUTION_TIMEOUT: int = 60
"""Timeout for dependency resolution in seconds."""

MAX_DEPENDENCY_DEPTH: int = 10
"""Maximum allowed dependency graph depth to prevent circular references."""


# ============================================================================
# Cache Configuration
# ============================================================================

RELEVANCE_CACHE_MAX_SIZE: int = 5000
"""Maximum number of relevance score entries to cache."""

CACHE_TTL_SECONDS: int = 3600
"""Default cache time-to-live in seconds (1 hour)."""

REDIS_CONNECTION_TIMEOUT: int = 5
"""Timeout for Redis connection in seconds."""

REDIS_RETRY_ATTEMPTS: int = 3
"""Number of retry attempts for Redis operations."""

REDIS_RETRY_BACKOFF: float = 0.5
"""Backoff multiplier for Redis retries in seconds."""


# ============================================================================
# Circuit Breaker Configuration
# ============================================================================

CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
"""Number of failures before opening circuit."""

CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60
"""Time in seconds before attempting recovery."""

CIRCUIT_BREAKER_SUCCESS_THRESHOLD: int = 2
"""Number of successes needed to close circuit."""


# ============================================================================
# Database Configuration
# ============================================================================

DATABASE_POOL_SIZE: int = 20
"""Maximum number of connections in the database pool."""

DATABASE_MAX_OVERFLOW: int = 10
"""Maximum number of overflow connections beyond pool size."""

DATABASE_POOL_TIMEOUT: int = 30
"""Timeout for acquiring database connection in seconds."""

DATABASE_POOL_RECYCLE: int = 3600
"""Recycle database connections after this many seconds (1 hour)."""

DATABASE_ECHO: bool = False
"""Enable SQL query logging."""

DATABASE_ISOLATION_LEVEL: str = "READ_COMMITTED"
"""Default transaction isolation level."""


# ============================================================================
# API Configuration
# ============================================================================

API_MAX_REQUEST_SIZE: int = 100 * 1024 * 1024
"""Maximum request body size in bytes (100 MB)."""

API_COMPRESSION_MIN_SIZE: int = 1000
"""Minimum response size to compress in bytes (1 KB)."""

API_COMPRESSION_LEVEL: int = 6
"""GZIP compression level (1-9, 6 is default balance)."""

API_RESPONSE_TIMEOUT: int = 300
"""Maximum time for API response in seconds (5 minutes)."""

API_WORKER_THREADS: int = 4
"""Number of worker threads for API server."""

# Allowed compression content types
API_COMPRESSED_CONTENT_TYPES: set[str] = {
    "application/json",
    "application/javascript",
    "text/plain",
    "text/html",
    "text/css",
    "text/xml",
    "application/xml",
}
"""Content types to compress (exclude pre-compressed like images)."""

# Paths to exclude from compression
API_COMPRESSION_EXCLUDE_PATHS: set[str] = {
    "/health",
    "/metrics",
    "/ping",
}
"""Paths to skip compression for."""


# ============================================================================
# Pagination Configuration
# ============================================================================

DEFAULT_PAGE_SIZE: int = 50
"""Default number of items per page."""

MAX_PAGE_SIZE: int = 500
"""Maximum allowed page size."""

MIN_PAGE_SIZE: int = 1
"""Minimum allowed page size."""


# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL: str = "INFO"
"""Default logging level."""

LOG_FORMAT: str = "json"
"""Logging output format (json or text)."""

LOG_RETENTION_DAYS: int = 30
"""Number of days to retain log files."""

LOG_MAX_FILE_SIZE_MB: int = 100
"""Maximum log file size before rotation in MB."""

LOG_BACKUP_COUNT: int = 10
"""Number of backup log files to keep."""

# Sensitive fields to redact from logs
LOG_REDACTED_FIELDS: set[str] = {
    "password",
    "token",
    "api_key",
    "secret",
    "credential",
    "auth",
}
"""Field names to redact from logs for security."""


# ============================================================================
# Validation Configuration
# ============================================================================

# Database URL validation patterns
VALID_DATABASE_SCHEMES: tuple[str, ...] = (
    "postgresql://",
    "postgres://",
    "mysql://",
    "sqlite://",
)
"""Valid database URL schemes."""

VALID_REDIS_SCHEME: str = "redis://"
"""Valid Redis URL scheme."""

# Field validation ranges
VALID_PORT_RANGE: tuple[int, int] = (1024, 65535)
"""Valid port number range (1024-65535)."""

VALID_LOG_LEVELS: set[str] = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}
"""Valid logging levels."""


# ============================================================================
# Cycle Time Monitoring Configuration (if applicable)
# ============================================================================

# Z-score threshold for anomaly detection
ANOMALY_ZSCORE_THRESHOLD: float = 2.5
"""Z-score threshold for cycle boundary anomaly detection.

Why 2.5?
- Standard normal: 99.4% of values have |z| < 3
- Z > 2.5 represents ~1.2% tail probability
- Balances sensitivity and false positive rate
- Tuned for cycle transition detection
"""

# Pattern detection thresholds
PATTERN_MIN_DATA_POINTS: int = 10
"""Minimum number of data points for pattern detection."""

PATTERN_MIN_PERIOD: int = 5
"""Minimum period in samples for pattern-based detection."""

AUTOCORRELATION_THRESHOLD: float = 0.5
"""Threshold for autocorrelation-based period detection.

Values > 0.5 indicate significant correlation, suggesting a repeating pattern.
"""

# Confidence scores for detection methods
CONFIDENCE_SIGNAL_BASED: float = 1.0
"""Confidence score for signal-based cycle detection (explicit markers)."""

CONFIDENCE_ANOMALY_BASED: float = 0.75
"""Confidence score for anomaly-based cycle detection."""

CONFIDENCE_PATTERN_BASED: float = 0.7
"""Confidence score for pattern-based cycle detection."""

# Severity thresholds for alerts
ALERT_SEVERITY_CRITICAL_FACTOR: float = 1.2
"""Multiplier for critical alerts (cycle > max * 1.2 or < min * 0.8)."""

ROLLING_WINDOW_BASE_DIVISOR: int = 20
"""Divisor for calculating adaptive rolling window size (len(data) / 20)."""

ROLLING_WINDOW_MIN_SIZE: int = 5
"""Minimum rolling window size for stability."""

MIN_CYCLE_DURATION_SECONDS: float = 1.0
"""Minimum cycle duration to prevent noise detection."""


# ============================================================================
# Helper Functions
# ============================================================================

def get_complexity_category(score: int) -> str:
    """Get complexity category name from score.

    Args:
        score: Complexity score (1-100)

    Returns:
        Category name: 'low', 'medium', or 'high'

    Raises:
        ValueError: If score is outside valid range
    """
    if not COMPLEXITY_MIN_SCORE <= score <= COMPLEXITY_MAX_SCORE:
        raise ValueError(
            f"Complexity score must be between "
            f"{COMPLEXITY_MIN_SCORE} and {COMPLEXITY_MAX_SCORE}, "
            f"got {score}"
        )

    for category, (min_score, max_score) in COMPLEXITY_SCORE_THRESHOLDS.items():
        if min_score <= score <= max_score:
            return category

    # Fallback (shouldn't reach here with proper bounds)
    return "high"


def validate_retry_configuration(max_retries: int, timeout: int) -> bool:
    """Validate retry configuration parameters.

    Args:
        max_retries: Maximum number of retries
        timeout: Timeout per attempt in seconds

    Returns:
        True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")

    if timeout < MIN_AGENT_TIMEOUT:
        raise ValueError(
            f"timeout must be at least {MIN_AGENT_TIMEOUT} seconds"
        )

    if timeout > MAX_AGENT_TIMEOUT:
        raise ValueError(
            f"timeout must not exceed {MAX_AGENT_TIMEOUT} seconds"
        )

    return True


if __name__ == "__main__":
    # Basic validation of constants
    print("Validating constants...")

    # Test complexity categories
    for score in [1, 30, 31, 60, 61, 100]:
        category = get_complexity_category(score)
        print(f"Score {score} -> {category}")

    # Test validation
    try:
        validate_retry_configuration(3, 300)
        print("Retry configuration validation: OK")
    except ValueError as e:
        print(f"Retry configuration validation: FAILED - {e}")

    print("All validations passed!")
