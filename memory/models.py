"""Pydantic models for the memory layer.

Defines structured data types for storing and retrieving cross-run knowledge.
"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid


class MemoryFact(BaseModel):
    """A single structured fact extracted from an agent run.

    Attributes:
        fact_id: Unique identifier for this fact
        category: Type of knowledge stored
        project_type: Project category for similarity matching
        tech_stack: Technologies used in the source project
        phase: Workflow phase where this fact was observed
        content: The actual knowledge content
        outcome: What happened as a result (resolution, cost, etc.)
        severity: Severity if this is a bug_pattern
        project_id: Source project identifier
        timestamp: When this fact was recorded
    """

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    fact_id: str = Field(default_factory=lambda: f"fact_{uuid.uuid4().hex[:12]}")
    category: Literal[
        "bug_pattern",
        "success_pattern",
        "tech_decision",
        "user_preference",
        "quality_metric",
    ]
    project_type: str
    tech_stack: list[str] = Field(default_factory=list)
    phase: str
    content: str
    outcome: str = ""
    severity: Optional[Literal["critical", "high", "medium", "low"]] = None
    project_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def matches_tech_stack(self, query_stack: list[str]) -> bool:
        """Check if this fact is relevant to a given tech stack."""
        if not query_stack or not self.tech_stack:
            return True
        query_lower = {t.lower() for t in query_stack}
        fact_lower = {t.lower() for t in self.tech_stack}
        return bool(query_lower & fact_lower)


class MemoryContext(BaseModel):
    """Pre-run context assembled from accumulated memory.

    Injected into every agent prompt via _build_project_context().

    Attributes:
        known_bug_patterns: Bug patterns to warn dev agents about
        successful_patterns: Patterns that worked well to encourage
        user_preferences: Accumulated style and tech preferences
        warning_flags: Critical one-liners to always include
        source_project_ids: Which past projects contributed this context
    """

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    known_bug_patterns: list[str] = Field(default_factory=list)
    successful_patterns: list[str] = Field(default_factory=list)
    user_preferences: dict[str, Any] = Field(default_factory=dict)
    warning_flags: list[str] = Field(default_factory=list)
    source_project_ids: list[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        """Return True if no meaningful context was found."""
        return not any([
            self.known_bug_patterns,
            self.successful_patterns,
            self.user_preferences,
            self.warning_flags,
        ])

    def to_prompt_section(self) -> str:
        """Render context as a markdown section for agent prompts."""
        if self.is_empty():
            return ""

        lines = ["## Memory Context (from past runs)\n"]

        if self.warning_flags:
            lines.append("### Critical Warnings")
            for flag in self.warning_flags[:5]:
                lines.append(f"- {flag}")
            lines.append("")

        if self.known_bug_patterns:
            lines.append("### Known Bug Patterns to Avoid")
            for pattern in self.known_bug_patterns[:8]:
                lines.append(f"- {pattern}")
            lines.append("")

        if self.successful_patterns:
            lines.append("### Proven Successful Patterns")
            for pattern in self.successful_patterns[:5]:
                lines.append(f"- {pattern}")
            lines.append("")

        if self.user_preferences:
            lines.append("### User Preferences")
            for key, val in list(self.user_preferences.items())[:5]:
                lines.append(f"- {key}: {val}")
            lines.append("")

        return "\n".join(lines)


class ObserverOutput(BaseModel):
    """Output from a single Observer Agent after a phase completes.

    Attributes:
        observer_type: Which observer produced this output
        phase: Phase that was observed
        facts: Extracted facts to store in memory
        summary: Human-readable summary of observations
    """

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    observer_type: Literal["technical", "quality", "metrics"]
    phase: str
    facts: list[MemoryFact] = Field(default_factory=list)
    summary: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
