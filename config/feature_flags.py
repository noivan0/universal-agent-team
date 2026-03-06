"""
Feature flags for gradual rollout of Phase 3+ optimizations.

Allows safe, incremental deployment of new features with rollout percentages.
Useful for A/B testing and gradual rollout strategies.

Example:
    from config.feature_flags import FeatureFlagManager, FeatureFlag

    flag_manager = FeatureFlagManager()

    # Start with 10% rollout
    flag_manager.enable(FeatureFlag.INCREMENTAL_STATE_UPDATES, rollout_percent=10)

    # Check if enabled for user
    if flag_manager.is_enabled(FeatureFlag.INCREMENTAL_STATE_UPDATES, user_id="user_123"):
        # Use new optimized code path
        pass
    else:
        # Use legacy code path
        pass
"""

import logging
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class FeatureFlag(Enum):
    """Feature flags for Phase 3+ optimizations."""

    # Phase 3 Optimizations
    INCREMENTAL_STATE_UPDATES = "incremental_state_updates"
    OPTIMIZED_DB_QUERIES = "optimized_db_queries"
    METRICS_COLLECTION = "metrics_collection"
    PERFORMANCE_MONITORING = "performance_monitoring"
    REQUEST_DEDUPLICATION = "request_deduplication"
    GRACEFUL_SHUTDOWN = "graceful_shutdown"

    # Future Features
    ML_COST_PREDICTION = "ml_cost_prediction"
    DISTRIBUTED_CACHING = "distributed_caching"
    ADVANCED_ANALYTICS = "advanced_analytics"


class FeatureFlagManager:
    """Manages feature flags with rollout percentages."""

    def __init__(self):
        """Initialize feature flag manager with defaults."""
        # Default flags status (all Phase 3 features off by default)
        self._flags: Dict[str, bool] = {
            FeatureFlag.INCREMENTAL_STATE_UPDATES.value: False,
            FeatureFlag.OPTIMIZED_DB_QUERIES.value: False,
            FeatureFlag.METRICS_COLLECTION.value: True,      # On by default for monitoring
            FeatureFlag.PERFORMANCE_MONITORING.value: True,  # On by default
            FeatureFlag.REQUEST_DEDUPLICATION.value: False,
            FeatureFlag.GRACEFUL_SHUTDOWN.value: True,       # On by default
            FeatureFlag.ML_COST_PREDICTION.value: False,
            FeatureFlag.DISTRIBUTED_CACHING.value: False,
            FeatureFlag.ADVANCED_ANALYTICS.value: False,
        }

        # Gradual rollout percentages (0-100)
        self._rollout_percentages: Dict[str, int] = {}

    def is_enabled(
        self,
        flag: FeatureFlag,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> bool:
        """
        Check if feature is enabled for user/project.

        Args:
            flag: Feature flag to check
            user_id: User ID for deterministic rollout
            project_id: Project ID for deterministic rollout

        Returns:
            True if feature is enabled for this user/project
        """
        flag_name = flag.value

        # Check if flag is enabled
        if not self._flags.get(flag_name, False):
            return False

        # Handle gradual rollout
        if flag_name in self._rollout_percentages:
            percentage = self._rollout_percentages[flag_name]

            if percentage == 100:
                # Fully rolled out
                return True

            if percentage == 0:
                # Rolled back
                return False

            # Deterministic rollout based on user/project ID
            identifier = user_id or project_id or "default"

            # Hash-based determination for consistent rollout
            hash_value = hash(identifier) % 100
            return hash_value < percentage

        return True

    def enable(
        self,
        flag: FeatureFlag,
        rollout_percent: int = 100,
    ) -> None:
        """
        Enable feature flag with optional rollout percentage.

        Args:
            flag: Feature flag to enable
            rollout_percent: Rollout percentage (0-100)

        Raises:
            ValueError: If rollout_percent not in valid range
        """
        if not (0 <= rollout_percent <= 100):
            raise ValueError("rollout_percent must be between 0 and 100")

        flag_name = flag.value
        self._flags[flag_name] = True
        self._rollout_percentages[flag_name] = rollout_percent

        logger.info(
            f"Feature '{flag_name}' enabled at {rollout_percent}% rollout"
        )

    def disable(self, flag: FeatureFlag) -> None:
        """
        Disable feature flag (instant rollback).

        Args:
            flag: Feature flag to disable
        """
        flag_name = flag.value
        self._flags[flag_name] = False
        logger.info(f"Feature '{flag_name}' disabled")

    def set_rollout(self, flag: FeatureFlag, percent: int) -> None:
        """
        Update rollout percentage for enabled feature.

        Args:
            flag: Feature flag to update
            percent: New rollout percentage (0-100)

        Raises:
            ValueError: If percent not in valid range
        """
        if not (0 <= percent <= 100):
            raise ValueError("percent must be between 0 and 100")

        flag_name = flag.value

        if not self._flags.get(flag_name, False):
            raise ValueError(f"Feature '{flag_name}' is not enabled")

        self._rollout_percentages[flag_name] = percent
        logger.info(f"Feature '{flag_name}' rollout updated to {percent}%")

    def get_status(self, flag: FeatureFlag) -> Dict[str, any]:
        """
        Get detailed status of a feature flag.

        Args:
            flag: Feature flag to check

        Returns:
            Dictionary with flag status and rollout info
        """
        flag_name = flag.value
        return {
            "flag": flag_name,
            "enabled": self._flags.get(flag_name, False),
            "rollout_percent": self._rollout_percentages.get(flag_name, 100),
        }

    def get_all_status(self) -> Dict[str, Dict[str, any]]:
        """
        Get status of all feature flags.

        Returns:
            Dictionary with all flag statuses
        """
        return {
            flag.value: self.get_status(flag)
            for flag in FeatureFlag
        }

    def reset_all(self) -> None:
        """Reset all feature flags to defaults."""
        for flag_name in self._flags.keys():
            self._flags[flag_name] = False
        self._rollout_percentages.clear()
        logger.info("All feature flags reset to defaults")


# Global feature flag manager instance
_feature_flag_manager = FeatureFlagManager()


def get_feature_flag_manager() -> FeatureFlagManager:
    """Get global feature flag manager."""
    return _feature_flag_manager


# Convenience functions
def is_feature_enabled(
    flag: FeatureFlag,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> bool:
    """Check if feature flag is enabled."""
    return _feature_flag_manager.is_enabled(flag, user_id, project_id)


def enable_feature(flag: FeatureFlag, rollout_percent: int = 100) -> None:
    """Enable feature flag."""
    _feature_flag_manager.enable(flag, rollout_percent)


def disable_feature(flag: FeatureFlag) -> None:
    """Disable feature flag."""
    _feature_flag_manager.disable(flag)
