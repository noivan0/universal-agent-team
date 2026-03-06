"""
Task manager for orchestrating agent execution.

Manages task lifecycle:
- Creation (from project requirements)
- Scheduling (respecting dependencies)
- Execution (running agents)
- Tracking (recording status and results)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# Task Models
# ============================================================================

class TaskStatus(str, Enum):
    """Status of a task."""
    PENDING = "pending"
    READY = "ready"  # Dependencies satisfied, ready to execute
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Blocked by failed dependency


class TaskRecord(BaseModel):
    """Record of a task execution."""
    task_id: str = Field(..., description="Unique task identifier")
    project_id: str = Field(..., description="Project this task belongs to")
    agent_id: str = Field(..., description="Agent to execute")
    phase: str = Field(..., description="Project phase")
    status: TaskStatus = Field(default=TaskStatus.PENDING)

    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list,
        description="Task IDs this task depends on"
    )

    # Execution tracking
    attempts: int = Field(default=0, description="Number of execution attempts")
    max_attempts: int = Field(default=3, description="Maximum attempts")
    errors: List[str] = Field(default_factory=list, description="Error messages")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Version tracking (for restart planning)
    agent_version: int = Field(default=1, description="Version of agent output")
    depends_on_versions: Dict[str, int] = Field(
        default_factory=dict,
        description="Versions of upstream agents"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Task Manager
# ============================================================================

class TaskManager:
    """
    Manages task creation, scheduling, and execution tracking.

    Tasks are persisted to: ~/.claude/projects/[project_id]/tasks/
    """

    @staticmethod
    def get_task_path(project_id: str, task_id: str) -> Path:
        """Get path to a task file."""
        tasks_dir = Path.home() / ".claude" / "projects" / project_id / "tasks"
        return tasks_dir / f"{task_id}.json"

    @staticmethod
    def get_all_tasks_dir(project_id: str) -> Path:
        """Get tasks directory for a project."""
        return Path.home() / ".claude" / "projects" / project_id / "tasks"

    @staticmethod
    def create_tasks_for_project(
        project_id: str,
        team_dependencies: Dict[str, List[str]]
    ) -> List[TaskRecord]:
        """
        Create tasks for all agents in the workflow.

        Args:
            project_id: Project ID
            team_dependencies: Dependency graph from team

        Returns:
            List of created TaskRecord objects
        """
        tasks = []
        phase_map = {
            "planning": "planning",
            "architecture": "architecture",
            "contract_validator": "contract_validation",
            "frontend": "development",
            "backend": "development",
            "qa": "testing",
            "documentation": "documentation"
        }

        for i, agent_id in enumerate(sorted(team_dependencies.keys())):
            task_id = f"task-{i:03d}-{agent_id}"
            phase = phase_map.get(agent_id, agent_id)

            task = TaskRecord(
                task_id=task_id,
                project_id=project_id,
                agent_id=agent_id,
                phase=phase,
                depends_on=[
                    f"task-{j:03d}-{dep}"
                    for j, dep in enumerate(sorted(team_dependencies.keys()))
                    if dep in team_dependencies.get(agent_id, [])
                ]
            )

            tasks.append(task)
            TaskManager.save_task(task, project_id)

        return tasks

    @staticmethod
    def save_task(task: TaskRecord, project_id: str):
        """Save task to disk."""
        task_path = TaskManager.get_task_path(project_id, task.task_id)
        task_path.parent.mkdir(parents=True, exist_ok=True)

        with open(task_path, "w") as f:
            json.dump(task.model_dump(), f, indent=2, default=str)

    @staticmethod
    def load_task(project_id: str, task_id: str) -> Optional[TaskRecord]:
        """Load task from disk."""
        task_path = TaskManager.get_task_path(project_id, task_id)

        if not task_path.exists():
            return None

        try:
            with open(task_path, "r") as f:
                data = json.load(f)
            return TaskRecord(**data)
        except Exception:
            return None

    @staticmethod
    def get_all_tasks(project_id: str) -> List[TaskRecord]:
        """Get all tasks for a project."""
        tasks_dir = TaskManager.get_all_tasks_dir(project_id)

        if not tasks_dir.exists():
            return []

        tasks = []
        for task_file in sorted(tasks_dir.glob("*.json")):
            task_id = task_file.stem
            task = TaskManager.load_task(project_id, task_id)
            if task:
                tasks.append(task)

        return tasks

    @staticmethod
    def get_ready_tasks(project_id: str) -> List[TaskRecord]:
        """
        Get all tasks that are ready to execute.

        A task is ready when:
        1. Status is PENDING or READY
        2. All dependencies are COMPLETED
        """
        all_tasks = TaskManager.get_all_tasks(project_id)
        completed_tasks = {
            t.task_id for t in all_tasks if t.status == TaskStatus.COMPLETED
        }

        ready_tasks = []
        for task in all_tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.READY]:
                if all(dep in completed_tasks for dep in task.depends_on):
                    ready_tasks.append(task)

        return ready_tasks

    @staticmethod
    def get_next_task(project_id: str) -> Optional[TaskRecord]:
        """Get the next task to execute (first ready task)."""
        ready_tasks = TaskManager.get_ready_tasks(project_id)
        return ready_tasks[0] if ready_tasks else None

    @staticmethod
    def update_task_status(
        project_id: str,
        task_id: str,
        new_status: TaskStatus,
        error: Optional[str] = None
    ):
        """Update task status."""
        task = TaskManager.load_task(project_id, task_id)

        if not task:
            return

        task.status = new_status

        if new_status == TaskStatus.IN_PROGRESS:
            task.started_at = datetime.now(timezone.utc)
            task.attempts += 1
        elif new_status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc)
            if task.started_at:
                task.duration_seconds = (task.completed_at - task.started_at).total_seconds()
        elif new_status == TaskStatus.FAILED:
            task.completed_at = datetime.now(timezone.utc)
            if error:
                task.errors.append(error)

        TaskManager.save_task(task, project_id)

    @staticmethod
    def mark_blocked_downstream(project_id: str, failed_task_id: str):
        """Mark all downstream tasks as blocked."""
        all_tasks = TaskManager.get_all_tasks(project_id)

        to_block = {failed_task_id}
        blocked = set()

        while to_block:
            current = to_block.pop()
            if current in blocked:
                continue

            blocked.add(current)

            for task in all_tasks:
                if current in task.depends_on:
                    to_block.add(task.task_id)

        for task in all_tasks:
            if task.task_id in blocked and task.task_id != failed_task_id:
                task.status = TaskStatus.BLOCKED
                TaskManager.save_task(task, project_id)

    @staticmethod
    def can_retry_task(project_id: str, task_id: str) -> bool:
        """Check if a task can be retried."""
        task = TaskManager.load_task(project_id, task_id)

        if not task:
            return False

        return task.attempts < task.max_attempts

    @staticmethod
    def reset_task_for_retry(project_id: str, task_id: str):
        """Reset task for retry (change status back to PENDING)."""
        task = TaskManager.load_task(project_id, task_id)

        if task:
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.completed_at = None
            task.duration_seconds = None
            # Keep attempts count for tracking
            TaskManager.save_task(task, project_id)

    @staticmethod
    def reset_downstream_tasks(project_id: str, task_id: str):
        """Reset all downstream tasks for re-execution."""
        all_tasks = TaskManager.get_all_tasks(project_id)

        to_reset = {task_id}
        reset_list = set()

        # Find all downstream tasks
        while to_reset:
            current = to_reset.pop()
            if current in reset_list:
                continue

            reset_list.add(current)

            for task in all_tasks:
                if current in task.depends_on:
                    to_reset.add(task.task_id)

        # Reset them
        for task in all_tasks:
            if task.task_id in reset_list:
                task.status = TaskStatus.PENDING
                task.started_at = None
                task.completed_at = None
                task.duration_seconds = None
                task.errors = []
                TaskManager.save_task(task, project_id)

    @staticmethod
    def get_task_status_summary(project_id: str) -> Dict[str, int]:
        """Get summary of task statuses."""
        tasks = TaskManager.get_all_tasks(project_id)

        summary = {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "ready": sum(1 for t in tasks if t.status == TaskStatus.READY),
            "in_progress": sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "blocked": sum(1 for t in tasks if t.status == TaskStatus.BLOCKED),
        }

        return summary

    @staticmethod
    def get_execution_time(project_id: str) -> Optional[float]:
        """Get total execution time for project."""
        tasks = TaskManager.get_all_tasks(project_id)
        completed = [t for t in tasks if t.duration_seconds]

        if not completed:
            return None

        return sum(t.duration_seconds for t in completed)
