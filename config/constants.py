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
# Brainstorming Configuration
# ============================================================================

BRAINSTORMING_MAX_TOKENS: int = 2048
"""Max tokens per brainstorming agent perspective (Full preliminary design depth)."""

BRAINSTORMING_SYNTHESIS_MAX_TOKENS: int = 3000
"""Max tokens for the synthesis agent that consolidates all perspectives."""

BRAINSTORMING_TEMPERATURE: float = 0.5
"""Temperature for brainstorming agents (higher than default 0.3 for more creativity)."""

BRAINSTORMING_ROLES: list[str] = [
    "planning",
    "architecture",
    "frontend",
    "backend",
    "qa",
    "documentation",
]
"""Domain roles participating in collective brainstorming."""


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
# Memory Layer Configuration
# ============================================================================

MEMORY_ENABLED: bool = True
"""Global toggle for cross-run memory system."""

SUPERMEMORY_API_KEY_ENV: str = "SUPERMEMORY_API_KEY"
"""Environment variable name for Supermemory API key."""

LOCAL_MEMORY_DIR: str = "~/.claude/memory"
"""Default local storage directory for JSON-based memory backend."""

MEMORY_RETENTION_DAYS: int = 90
"""Number of days to retain memory facts before they are ignored on retrieval."""

OBSERVER_MAX_TOKENS: int = 2048
"""Max tokens per Observer Agent (3 run in parallel after each phase)."""

MEMORY_SEARCH_MAX_TOKENS: int = 2048
"""Max tokens per Search Agent (3 run in parallel before each workflow)."""

OBSERVER_TEMPERATURE: float = 0.2
"""Temperature for Observer Agents (low — structured fact extraction)."""

MEMORY_SEARCH_TEMPERATURE: float = 0.2
"""Temperature for Search Agents (low — focused retrieval)."""

MEMORY_MAX_BUG_PATTERNS: int = 8
"""Maximum bug patterns to inject into agent context."""

MEMORY_MAX_SUCCESS_PATTERNS: int = 5
"""Maximum success patterns to inject into agent context."""

MEMORY_MAX_WARNING_FLAGS: int = 5
"""Maximum critical warnings to inject into agent context."""

MEMORY_SEARCH_LIMIT: int = 20
"""Maximum facts returned per Search Agent query."""


# ============================================================================
# Evaluator Agent Configuration
# ============================================================================

EVALUATOR_THRESHOLD: float = 6.5
"""Weighted average score below which Evaluator triggers dev agent re-run."""

MAX_EVALUATOR_ROUNDS: int = 2
"""Maximum Evaluator → dev agents iteration rounds (separate from QA healing loop)."""

EVALUATOR_MAX_TOKENS: int = 4096
"""Max tokens for Evaluator Agent response."""

EVALUATOR_TEMPERATURE: float = 0.1
"""Temperature for Evaluator Agent (very low — consistent rubric scoring)."""

# Rubric criterion weights (must sum to 1.0)
EVALUATOR_WEIGHTS: dict[str, float] = {
    "architecture_coherence": 0.30,  # Does code faithfully implement the spec?
    "feature_completeness": 0.35,    # No stubs/placeholders — actually implemented?
    "code_quality": 0.20,            # TypeScript types, Ruff, consistent structure
    "functionality": 0.15,           # API integration accuracy, business logic
}
"""Rubric weights for the independent Evaluator Agent."""

EVALUATOR_MIN_SCORE_PER_CRITERION: float = 4.0
"""Any single criterion below this triggers re-run regardless of weighted average."""


# ============================================================================
# Extended Thinking Configuration
# ============================================================================

THINKING_BUDGET_EVALUATOR: int = 0
"""Token budget for extended thinking in Evaluator Agent.
Set to 0 (disabled) — enterprise proxy environments typically have lower token limits
that cause JSON truncation when thinking consumes the output budget.
Re-enable by setting to 3000-5000 if your API endpoint supports extended thinking."""

THINKING_BUDGET_ARCHITECTURE: int = 0
"""Token budget for extended thinking in Architecture Agent.
Set to 0 (disabled) — same reason as THINKING_BUDGET_EVALUATOR.
Re-enable by setting to 5000-8000 if your API endpoint supports extended thinking."""


# ============================================================================
# Adversarial Agent Configuration
# ============================================================================

ADVERSARIAL_ENABLED: bool = True
"""Whether to run the Adversarial Agent after architecture (pre-development review)."""

ADVERSARIAL_MAX_TOKENS: int = 2048
"""Max tokens for Adversarial Agent response."""

ADVERSARIAL_TEMPERATURE: float = 0.3
"""Temperature for Adversarial Agent."""


# ============================================================================
# Reflexion Loop Configuration
# ============================================================================

REFLEXION_ENABLED: bool = False
"""Whether agents self-review their own output (adds ~30% tokens per agent)."""

REFLEXION_MAX_TOKENS: int = 4096
"""Max tokens for reflexion self-review pass."""

REFLEXION_TEMPERATURE: float = 0.2
"""Temperature for reflexion self-review (low — focused correction)."""


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
