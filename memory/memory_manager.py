"""Central memory manager — entry point for all memory operations.

Provides a unified interface over local/supermemory backends and manages
the singleton instance used across a workflow run.
"""

import logging
import os
from typing import Optional

from memory.models import MemoryFact, MemoryContext, ObserverOutput
from memory.backends.local_backend import LocalMemoryBackend
from config.constants import (
    LOCAL_MEMORY_DIR,
    MEMORY_RETENTION_DAYS,
    SUPERMEMORY_API_KEY_ENV,
    MEMORY_MAX_BUG_PATTERNS,
    MEMORY_MAX_SUCCESS_PATTERNS,
    MEMORY_MAX_WARNING_FLAGS,
    MEMORY_SEARCH_LIMIT,
)

logger = logging.getLogger(__name__)

# Module-level singleton
_memory_manager: Optional["MemoryManager"] = None


def get_memory_manager() -> "MemoryManager":
    """Return the module-level MemoryManager singleton, creating it if needed."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def reset_memory_manager() -> None:
    """Reset the singleton (useful for testing)."""
    global _memory_manager
    _memory_manager = None


class MemoryManager:
    """Unified interface for cross-run memory storage and retrieval.

    Automatically selects the best available backend:
    - SupermemoryBackend if SUPERMEMORY_API_KEY env var is set
    - LocalMemoryBackend otherwise (JSON files, no dependencies)

    Args:
        base_dir: Override local storage directory.
        retention_days: How long to keep facts.
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        retention_days: int = MEMORY_RETENTION_DAYS,
    ) -> None:
        api_key = os.environ.get(SUPERMEMORY_API_KEY_ENV)

        if api_key:
            try:
                from memory.backends.supermemory_backend import SupermemoryBackend
                self._backend = SupermemoryBackend(api_key=api_key)
                logger.info("Memory: using Supermemory backend")
            except ImportError:
                logger.warning(
                    "Supermemory SDK not installed (pip install supermemory). "
                    "Falling back to local backend."
                )
                self._backend = LocalMemoryBackend(
                    base_dir=base_dir or LOCAL_MEMORY_DIR,
                    retention_days=retention_days,
                )
        else:
            self._backend = LocalMemoryBackend(
                base_dir=base_dir or LOCAL_MEMORY_DIR,
                retention_days=retention_days,
            )
            logger.debug("Memory: using local backend at %s", LOCAL_MEMORY_DIR)

    # -----------------------------------------------------------------------
    # Storage
    # -----------------------------------------------------------------------

    def store_fact(self, fact: MemoryFact) -> None:
        """Store a single fact."""
        self._backend.store(fact)

    def search(
        self,
        *,
        category: Optional[str] = None,
        project_type: Optional[str] = None,
        tech_stack: Optional[list[str]] = None,
        phase: Optional[str] = None,
        limit: int = 20,
    ) -> list[MemoryFact]:
        """Public search interface delegating to the active backend."""
        return self._backend.search(
            category=category,
            project_type=project_type,
            tech_stack=tech_stack,
            phase=phase,
            limit=limit,
        )

    def store_observer_output(self, output: ObserverOutput) -> None:
        """Store all facts extracted by an Observer Agent."""
        if output.facts:
            self._backend.store_many(output.facts)
            logger.debug(
                "Stored %d facts from %s observer (phase: %s)",
                len(output.facts),
                output.observer_type,
                output.phase,
            )

    # -----------------------------------------------------------------------
    # Retrieval
    # -----------------------------------------------------------------------

    def build_context(
        self,
        project_type: str,
        tech_stack: Optional[list[str]] = None,
    ) -> MemoryContext:
        """Assemble a MemoryContext from stored facts.

        Args:
            project_type: Project category for similarity filtering.
            tech_stack: Technologies to filter by.

        Returns:
            MemoryContext ready to inject into agent prompts.
        """
        bug_facts = self._backend.search(
            category="bug_pattern",
            project_type=project_type,
            tech_stack=tech_stack,
            limit=MEMORY_SEARCH_LIMIT,
        )
        success_facts = self._backend.search(
            category="success_pattern",
            project_type=project_type,
            tech_stack=tech_stack,
            limit=MEMORY_SEARCH_LIMIT,
        )
        pref_facts = self._backend.search(
            category="user_preference",
            limit=10,
        )

        # Extract content strings
        bug_patterns = [f.content for f in bug_facts[:MEMORY_MAX_BUG_PATTERNS]]
        success_patterns = [f.content for f in success_facts[:MEMORY_MAX_SUCCESS_PATTERNS]]

        # Warning flags = critical bug patterns (severity=critical)
        warning_flags = [
            f.content
            for f in bug_facts
            if f.severity == "critical"
        ][:MEMORY_MAX_WARNING_FLAGS]

        # User preferences
        user_prefs: dict = {}
        for fact in pref_facts:
            try:
                import json
                prefs = json.loads(fact.content)
                if isinstance(prefs, dict):
                    user_prefs.update(prefs)
            except Exception:
                pass

        source_ids = list({f.project_id for f in bug_facts + success_facts})

        ctx = MemoryContext(
            known_bug_patterns=bug_patterns,
            successful_patterns=success_patterns,
            user_preferences=user_prefs,
            warning_flags=warning_flags,
            source_project_ids=source_ids[:10],
        )

        if not ctx.is_empty():
            logger.info(
                "Memory context: %d bug patterns, %d success patterns, %d warnings",
                len(bug_patterns),
                len(success_patterns),
                len(warning_flags),
            )

        return ctx

    def stats(self) -> dict[str, int]:
        """Return fact counts per category."""
        return self._backend.count()
