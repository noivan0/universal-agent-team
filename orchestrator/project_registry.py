"""
Project registry for managing project configurations and state.

Each project is independently managed with its own:
- Configuration (user request, tech stack, status)
- Tasks (planning, architecture, frontend, backend, qa, documentation)
- State snapshots (for each phase)

Uses BaseRegistry for caching and persistence (Quick Win 3).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator

from orchestrator.base_registry import BaseRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class ProjectPhase(str, Enum):
    """Project execution phase."""
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    COMPLETE = "complete"
    FAILED = "failed"


class ProjectStatus(str, Enum):
    """Project overall status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETE = "complete"
    FAILED = "failed"


# ============================================================================
# Project Configuration Model
# ============================================================================

class ProjectConfig(BaseModel):
    """Configuration for a project."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    project_id: str = Field(..., description="Unique project identifier")
    team_id: str = Field(
        "universal-agents-v1",
        description="Team to use for this project"
    )
    user_request: str = Field(..., description="User's project description")
    context: Optional[str] = Field(None, description="Additional context")

    # Tech stack (auto-detected by Planning Agent)
    tech_stack: Optional[Dict[str, Optional[str]]] = Field(
        default=None,
        description="Detected tech stack {frontend, backend}"
    )

    # Complexity scoring (set by Planning Agent)
    complexity_score: Optional[int] = Field(
        None,
        description="Project complexity (1-100)"
    )

    # Status tracking
    status: ProjectStatus = Field(default=ProjectStatus.PENDING)
    current_phase: ProjectPhase = Field(default=ProjectPhase.PLANNING)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error tracking
    error_message: Optional[str] = None
    requires_human_approval: bool = False
    approval_reason: Optional[str] = None

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("project_id cannot be empty")
        # Only allow alphanumeric, dash, underscore
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("project_id must contain only alphanumeric, dash, underscore")
        return v


# ============================================================================
# Project Registry
# ============================================================================

class ProjectRegistry(BaseRegistry[ProjectConfig]):
    """
    Manages project configurations and metadata.

    Extends BaseRegistry for caching and persistence.
    Projects are stored in: ~/.claude/projects/[project_id]/
    Each project has:
    - project.json: Configuration
    - tasks/: Task records
    - state/: State snapshots
    """

    REGISTRY_BASE = Path.home() / ".claude" / "projects"

    def __init__(self):
        """Initialize project registry."""
        super().__init__(str(ProjectRegistry.REGISTRY_BASE))

    def _parse_config(self, data: dict) -> ProjectConfig:
        """Parse raw data into ProjectConfig."""
        return ProjectConfig(**data)

    def _get_config_filename(self, key: str) -> str:
        """Get filename for a project key."""
        return f"{key}_project.json"

    def validate_config(self, config: ProjectConfig) -> bool:
        """Validate project configuration.

        Args:
            config: ProjectConfig to validate

        Returns:
            True if valid, False otherwise
        """
        # Call parent validation (Pydantic)
        if not super().validate_config(config):
            return False

        # Custom validation rules
        if not config.project_id or len(config.project_id) < 3:
            logger.error("project_id must be at least 3 characters")
            return False

        if not config.user_request or len(config.user_request.strip()) < 10:
            logger.error("user_request must be at least 10 characters")
            return False

        if config.complexity_score is not None:
            if not (1 <= config.complexity_score <= 100):
                logger.error("complexity_score must be between 1-100")
                return False

        return True

    @staticmethod
    def get_project_dir(project_id: str) -> Path:
        """Get directory for a project."""
        return ProjectRegistry.REGISTRY_BASE / project_id

    @staticmethod
    def get_tasks_dir(project_id: str) -> Path:
        """Get tasks directory for a project."""
        return ProjectRegistry.get_project_dir(project_id) / "tasks"

    @staticmethod
    def get_state_dir(project_id: str) -> Path:
        """Get state directory for a project."""
        return ProjectRegistry.get_project_dir(project_id) / "state"

    @staticmethod
    def get_config_path(project_id: str) -> Path:
        """Get project config file path."""
        return ProjectRegistry.get_project_dir(project_id) / "project.json"

    @staticmethod
    def ensure_directories(project_id: str):
        """Ensure all project directories exist."""
        ProjectRegistry.get_project_dir(project_id).mkdir(parents=True, exist_ok=True)
        ProjectRegistry.get_tasks_dir(project_id).mkdir(parents=True, exist_ok=True)
        ProjectRegistry.get_state_dir(project_id).mkdir(parents=True, exist_ok=True)

    # Class-level instance for backward compatibility
    _instance: Optional['ProjectRegistry'] = None

    @classmethod
    def _get_instance(cls) -> 'ProjectRegistry':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def create_project(
        cls,
        project_id: str,
        user_request: str,
        team_id: str = "universal-agents-v1",
        context: Optional[str] = None
    ) -> ProjectConfig:
        """
        Create a new project.

        Args:
            project_id: Unique project identifier
            user_request: User's project description
            team_id: Team to use (default: universal-agents-v1)
            context: Optional additional context

        Returns:
            Created ProjectConfig
        """
        config = ProjectConfig(
            project_id=project_id,
            team_id=team_id,
            user_request=user_request,
            context=context
        )

        cls.ensure_directories(project_id)
        cls._get_instance().save(project_id, config)

        return config

    @staticmethod
    def save_project_config(config: ProjectConfig):
        """Save project config to disk (backward compatible)."""
        ProjectRegistry._get_instance().save(config.project_id, config)

    @staticmethod
    def load_project_config(project_id: str) -> Optional[ProjectConfig]:
        """
        Load project config from disk (backward compatible).

        Args:
            project_id: Project identifier

        Returns:
            ProjectConfig if found, None otherwise
        """
        return ProjectRegistry._get_instance().load(project_id)

    @staticmethod
    def get_all_projects() -> List[ProjectConfig]:
        """Get all projects."""
        instance = ProjectRegistry._get_instance()
        return list(instance.list_all().values())

    @staticmethod
    def project_exists(project_id: str) -> bool:
        """Check if a project exists."""
        return ProjectRegistry._get_instance().exists(project_id)

    @staticmethod
    def delete_project(project_id: str):
        """Delete a project (including all tasks and state)."""
        instance = ProjectRegistry._get_instance()
        instance.delete(project_id)

        project_dir = ProjectRegistry.get_project_dir(project_id)
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)

    @staticmethod
    def get_project_summary(project_id: str) -> Dict[str, Any]:
        """Get a summary of project status."""
        config = ProjectRegistry.load_project_config(project_id)

        if not config:
            return {}

        return {
            "project_id": config.project_id,
            "team_id": config.team_id,
            "status": config.status.value,
            "current_phase": config.current_phase.value,
            "complexity_score": config.complexity_score,
            "created_at": config.created_at.isoformat(),
            "requires_human_approval": config.requires_human_approval
        }

    @staticmethod
    def update_project_phase(project_id: str, new_phase: ProjectPhase):
        """Update project's current phase."""
        config = ProjectRegistry.load_project_config(project_id)
        if config:
            config.current_phase = new_phase
            ProjectRegistry.save_project_config(config)

    @staticmethod
    def update_project_status(
        project_id: str,
        new_status: ProjectStatus,
        error_message: Optional[str] = None
    ):
        """Update project's overall status."""
        config = ProjectRegistry.load_project_config(project_id)
        if config:
            config.status = new_status
            if error_message:
                config.error_message = error_message
            if new_status == ProjectStatus.COMPLETE:
                config.completed_at = datetime.now(timezone.utc)
            elif new_status == ProjectStatus.IN_PROGRESS and not config.started_at:
                config.started_at = datetime.now(timezone.utc)
            ProjectRegistry.save_project_config(config)

    @staticmethod
    def set_human_approval_needed(project_id: str, reason: str):
        """Mark project as needing human approval."""
        config = ProjectRegistry.load_project_config(project_id)
        if config:
            config.requires_human_approval = True
            config.approval_reason = reason
            config.status = ProjectStatus.PAUSED
            ProjectRegistry.save_project_config(config)

    @staticmethod
    def clear_human_approval(project_id: str):
        """Clear human approval requirement."""
        config = ProjectRegistry.load_project_config(project_id)
        if config:
            config.requires_human_approval = False
            config.approval_reason = None
            config.status = ProjectStatus.IN_PROGRESS
            ProjectRegistry.save_project_config(config)
