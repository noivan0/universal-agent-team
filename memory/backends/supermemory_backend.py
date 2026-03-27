"""Supermemory.ai API backend for cross-run memory storage.

Activated automatically when SUPERMEMORY_API_KEY environment variable is set.

Requires: pip install supermemory

Supermemory stores facts as "memories" with metadata tags for filtering.
Tags are used to replicate the category/project_type/tech_stack filtering
that the LocalMemoryBackend does via directory structure.

See: https://github.com/supermemoryai/supermemory
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from memory.models import MemoryFact

logger = logging.getLogger(__name__)


class SupermemoryBackend:
    """Memory backend using Supermemory.ai API.

    Args:
        api_key: Supermemory API key.
        base_url: Optional API base URL override.
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None) -> None:
        try:
            import supermemory  # type: ignore
            self._client = supermemory.Supermemory(api_key=api_key)
            if base_url:
                self._client.base_url = base_url
        except ImportError as e:
            raise ImportError(
                "supermemory package not found. Install with: pip install supermemory"
            ) from e
        self._api_key = api_key
        logger.info("SupermemoryBackend initialised")

    def _fact_to_memory_text(self, fact: MemoryFact) -> str:
        """Serialise a MemoryFact to a human-readable string for storage."""
        lines = [
            f"Category: {fact.category}",
            f"Phase: {fact.phase}",
            f"Content: {fact.content}",
        ]
        if fact.outcome:
            lines.append(f"Outcome: {fact.outcome}")
        if fact.severity:
            lines.append(f"Severity: {fact.severity}")
        return "\n".join(lines)

    def store(self, fact: MemoryFact) -> None:
        """Store a MemoryFact as a Supermemory memory.

        The raw_json field in metadata enables full reconstruction on retrieval.
        Client-side filtering (category, project_type, tech_stack) is applied
        after semantic search because Supermemory's search API does not support
        structured tag filtering.
        """
        try:
            self._client.memories.add(
                content=self._fact_to_memory_text(fact),
                metadata={
                    "fact_id": fact.fact_id,
                    "timestamp": fact.timestamp.isoformat(),
                    "raw_json": fact.model_dump_json(),
                },
            )
            logger.debug("Supermemory: stored fact %s", fact.fact_id)
        except Exception as e:
            logger.warning("Supermemory store failed for %s: %s", fact.fact_id, e)

    def store_many(self, facts: list[MemoryFact]) -> None:
        """Store multiple facts."""
        for fact in facts:
            self.store(fact)

    def search(
        self,
        *,
        category: Optional[str] = None,
        project_type: Optional[str] = None,
        tech_stack: Optional[list[str]] = None,
        phase: Optional[str] = None,
        limit: int = 20,
    ) -> list[MemoryFact]:
        """Search Supermemory for relevant facts.

        Builds a semantic query from filters and retrieves matching memories,
        then reconstructs MemoryFact objects from stored raw_json metadata.

        Args:
            category: Filter by fact category.
            project_type: Filter by project type.
            tech_stack: Filter by technology overlap.
            phase: Filter by workflow phase.
            limit: Maximum facts to return.

        Returns:
            List of MemoryFact objects, newest first.
        """
        # Build a semantic search query
        query_parts = []
        if category:
            query_parts.append(category.replace("_", " "))
        if project_type:
            query_parts.append(project_type)
        if tech_stack:
            query_parts.append(" ".join(tech_stack[:3]))
        if phase:
            query_parts.append(f"phase {phase}")

        query = " ".join(query_parts) if query_parts else "software development issues"

        try:
            results = self._client.memories.search(query=query, limit=limit * 2)
        except Exception as e:
            logger.warning("Supermemory search failed: %s", e)
            return []

        facts: list[MemoryFact] = []
        for result in results:
            # Try to reconstruct MemoryFact from stored raw_json
            try:
                meta = getattr(result, "metadata", {}) or {}
                raw_json = meta.get("raw_json")
                if raw_json:
                    fact = MemoryFact.model_validate_json(raw_json)
                else:
                    # Fallback: parse from content text if raw_json not available
                    continue

                # Apply client-side filters (Supermemory uses semantic search)
                if category and fact.category != category:
                    continue
                if project_type and project_type.lower() not in fact.project_type.lower():
                    continue
                if tech_stack and not fact.matches_tech_stack(tech_stack):
                    continue
                if phase and fact.phase != phase:
                    continue

                facts.append(fact)
                if len(facts) >= limit:
                    break
            except Exception as e:
                logger.debug("Skipping malformed Supermemory result: %s", e)

        facts.sort(key=lambda f: f.timestamp, reverse=True)
        return facts

    def count(self) -> dict[str, int]:
        """Return approximate fact counts via category-filtered search."""
        categories = [
            "bug_pattern", "success_pattern", "tech_decision",
            "user_preference", "quality_metric",
        ]
        counts: dict[str, int] = {}
        for cat in categories:
            try:
                facts = self.search(category=cat, limit=200)
                counts[cat] = len(facts)
            except Exception:
                counts[cat] = 0
        return counts
