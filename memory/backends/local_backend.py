"""Local JSON file-based memory backend.

Default backend — works with no external dependencies.
Stores facts as JSON files under ~/.claude/memory/.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from memory.models import MemoryFact

logger = logging.getLogger(__name__)


class LocalMemoryBackend:
    """File-based memory store using ~/.claude/memory/.

    Directory structure:
        ~/.claude/memory/
            bug_pattern/
                fact_abc123.json
                ...
            success_pattern/
                ...
            tech_decision/
                ...
            user_preference/
                ...
            quality_metric/
                ...

    Args:
        base_dir: Root directory for memory storage. Defaults to ~/.claude/memory.
        retention_days: Facts older than this are ignored on retrieval.
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        retention_days: int = 90,
    ) -> None:
        if base_dir is None:
            base_dir = os.path.expanduser("~/.claude/memory")
        self.base_dir = Path(base_dir)
        self.retention_days = retention_days
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create category directories if they don't exist."""
        categories = [
            "bug_pattern",
            "success_pattern",
            "tech_decision",
            "user_preference",
            "quality_metric",
        ]
        for cat in categories:
            (self.base_dir / cat).mkdir(parents=True, exist_ok=True)

    def store(self, fact: MemoryFact) -> None:
        """Persist a single MemoryFact to disk.

        Args:
            fact: The fact to store.
        """
        path = self.base_dir / fact.category / f"{fact.fact_id}.json"
        try:
            path.write_text(
                json.dumps(fact.model_dump(mode="json"), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Stored memory fact %s (%s)", fact.fact_id, fact.category)
        except OSError as e:
            logger.warning("Failed to store memory fact %s: %s", fact.fact_id, e)

    def store_many(self, facts: list[MemoryFact]) -> None:
        """Persist multiple facts."""
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
        """Retrieve facts matching the given filters.

        Args:
            category: Filter by category (e.g. "bug_pattern").
            project_type: Filter by project type substring match.
            tech_stack: Filter by tech stack overlap.
            phase: Filter by workflow phase.
            limit: Maximum number of facts to return.

        Returns:
            List of matching MemoryFact objects, newest first.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        results: list[MemoryFact] = []

        search_dirs = []
        if category:
            cat_dir = self.base_dir / category
            if cat_dir.exists():
                search_dirs.append(cat_dir)
        else:
            search_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]

        for cat_dir in search_dirs:
            for path in cat_dir.glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    fact = MemoryFact.model_validate(data)
                except Exception as e:
                    logger.debug("Skipping invalid fact file %s: %s", path, e)
                    continue

                # Age filter
                if fact.timestamp < cutoff:
                    continue

                # Project type filter
                if project_type and project_type.lower() not in fact.project_type.lower():
                    continue

                # Tech stack filter
                if tech_stack and not fact.matches_tech_stack(tech_stack):
                    continue

                # Phase filter
                if phase and fact.phase != phase:
                    continue

                results.append(fact)

        # Sort newest first, apply limit
        results.sort(key=lambda f: f.timestamp, reverse=True)
        return results[:limit]

    def count(self) -> dict[str, int]:
        """Return fact count per category."""
        counts: dict[str, int] = {}
        for cat_dir in self.base_dir.iterdir():
            if cat_dir.is_dir():
                counts[cat_dir.name] = len(list(cat_dir.glob("*.json")))
        return counts
