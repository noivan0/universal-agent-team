"""
Orchestrator module for Universal Agent Team.

Manages multi-agent orchestration, project execution, and task coordination.
"""

__version__ = "1.0.0"

from orchestrator.project_registry import ProjectRegistry, ProjectConfig
from orchestrator.team_registry import TeamRegistry, TeamConfig
from orchestrator.task_manager import TaskManager, TaskManager as TaskExecutor
from orchestrator.orchestrator import ProjectOrchestrator

__all__ = [
    "ProjectRegistry",
    "ProjectConfig",
    "TeamRegistry",
    "TeamConfig",
    "TaskManager",
    "TaskExecutor",
    "ProjectOrchestrator",
]
