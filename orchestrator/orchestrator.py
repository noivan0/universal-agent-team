"""
ProjectOrchestrator: Main orchestration engine for multi-agent workflows.

Coordinates agent execution, manages state, handles errors, and enables
intelligent restart planning based on failures.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from state_models import AgentState, create_initial_state, apply_state_update
from dependency_context import DependencyContextLoader, RestartImpactAnalyzer
from checkpoint_manager import CheckpointManager, StreamingExecutionHandler

from orchestrator.project_registry import ProjectRegistry, ProjectConfig, ProjectStatus, ProjectPhase
from orchestrator.team_registry import TeamRegistry, TeamConfig
from orchestrator.task_manager import TaskManager, TaskStatus, TaskRecord


# ============================================================================
# Orchestrator Configuration
# ============================================================================

class OrchestratorConfig:
    """Configuration for orchestrator behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        checkpoint_enabled: bool = True,
        parallel_execution: bool = True,
        verbose: bool = False
    ):
        self.max_retries = max_retries
        self.checkpoint_enabled = checkpoint_enabled
        self.parallel_execution = parallel_execution
        self.verbose = verbose


# ============================================================================
# ProjectOrchestrator
# ============================================================================

class ProjectOrchestrator:
    """
    Orchestrates multi-agent execution for a project.

    Responsibilities:
    1. Load project configuration and team spec
    2. Create/load project state
    3. Execute agents in dependency order
    4. Handle failures with intelligent restart
    5. Track progress and manage checkpoints
    """

    def __init__(
        self,
        project_id: str,
        config: Optional[OrchestratorConfig] = None
    ):
        """
        Initialize orchestrator for a project.

        Args:
            project_id: Project to orchestrate
            config: Orchestrator configuration
        """
        self.project_id = project_id
        self.config = config or OrchestratorConfig()
        self.logger = self._setup_logger()

        # Load project and team
        self.project_config = ProjectRegistry.load_project_config(project_id)
        if not self.project_config:
            raise ValueError(f"Project not found: {project_id}")

        self.team_config = TeamRegistry.load_team_config(self.project_config.team_id)
        if not self.team_config:
            raise ValueError(f"Team not found: {self.project_config.team_id}")

        # Load or create state
        self.state = self._load_or_create_state()

        # Create tasks if not exist
        self._ensure_tasks_created()

        self.logger.info(
            f"Orchestrator initialized for project {project_id} "
            f"using team {self.project_config.team_id}"
        )

    def _setup_logger(self) -> logging.Logger:
        """Setup logging."""
        logger = logging.getLogger(f"orchestrator.{self.project_id}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f"[%(name)s] %(levelname)s: %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG if self.config.verbose else logging.INFO)
        return logger

    def _load_or_create_state(self) -> AgentState:
        """Load existing state or create new one."""
        state_file = ProjectRegistry.get_state_dir(self.project_id) / "current_state.json"

        if state_file.exists():
            self.logger.info("Loading existing project state")
            # In Phase 2, we'll implement state loading from JSON
            # For now, create fresh state
            pass

        self.logger.info("Creating new project state")
        state = create_initial_state(
            project_id=self.project_id,
            user_request=self.project_config.user_request,
            tech_stack=self.project_config.tech_stack
        )

        return state

    def _ensure_tasks_created(self):
        """Ensure all tasks are created for this project."""
        existing_tasks = TaskManager.get_all_tasks(self.project_id)

        if not existing_tasks:
            self.logger.info("Creating tasks for all agents")
            TaskManager.create_tasks_for_project(
                self.project_id,
                self.team_config.dependencies
            )

    def get_current_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        summary = TaskManager.get_task_status_summary(self.project_id)
        execution_time = TaskManager.get_execution_time(self.project_id)

        return {
            "project_id": self.project_id,
            "project_status": self.project_config.status.value,
            "current_phase": self.project_config.current_phase.value,
            "task_summary": summary,
            "total_execution_time_seconds": execution_time,
            "requires_human_approval": self.project_config.requires_human_approval,
            "approval_reason": self.project_config.approval_reason
        }

    def can_proceed(self) -> bool:
        """Check if project can proceed (no human approval needed)."""
        return not self.project_config.requires_human_approval

    def get_next_task(self) -> Optional[TaskRecord]:
        """Get the next task to execute."""
        return TaskManager.get_next_task(self.project_id)

    def execute_task(self, task: TaskRecord) -> bool:
        """
        Execute a single task (agent).

        Args:
            task: Task to execute

        Returns:
            True if execution successful, False otherwise
        """
        self.logger.info(f"Executing task: {task.task_id} (agent: {task.agent_id})")

        # Update project status
        if self.project_config.status != ProjectStatus.IN_PROGRESS:
            ProjectRegistry.update_project_status(
                self.project_id,
                ProjectStatus.IN_PROGRESS
            )

        # Load context for this agent
        context = DependencyContextLoader.load_context_for_agent(
            self.state,
            task.agent_id
        )

        tokens = DependencyContextLoader.estimate_tokens_for_agent(self.state, task.agent_id)
        self.logger.debug(f"Agent context size: {tokens} tokens")

        # Update task status
        TaskManager.update_task_status(self.project_id, task.task_id, TaskStatus.IN_PROGRESS)

        try:
            # In Phase 2, implement actual agent execution
            # For now, just mark as completed
            self.logger.info(f"Task {task.task_id} simulated execution")

            TaskManager.update_task_status(self.project_id, task.task_id, TaskStatus.COMPLETED)
            return True

        except Exception as e:
            self.logger.error(f"Task {task.task_id} failed: {e}")
            TaskManager.update_task_status(
                self.project_id,
                task.task_id,
                TaskStatus.FAILED,
                error=str(e)
            )

            # Mark downstream as blocked
            TaskManager.mark_blocked_downstream(self.project_id, task.task_id)

            return False

    def handle_task_failure(self, task: TaskRecord) -> bool:
        """
        Handle task failure with intelligent restart planning.

        Args:
            task: Failed task

        Returns:
            True if recovery attempted, False if escalation needed
        """
        self.logger.warning(f"Handling failure for task: {task.task_id}")

        # In Phase 2, implement error analysis from QA Agent
        # For now, just retry if possible
        if TaskManager.can_retry_task(self.project_id, task.task_id):
            self.logger.info(f"Retrying task: {task.task_id} "
                           f"(attempt {task.attempts + 1}/{task.max_attempts})")

            TaskManager.reset_task_for_retry(self.project_id, task.task_id)
            return True

        else:
            self.logger.error(f"Max retries exceeded for task: {task.task_id}")
            ProjectRegistry.set_human_approval_needed(
                self.project_id,
                f"Task {task.task_id} failed after {task.max_attempts} attempts"
            )
            return False

    def execute_workflow(self) -> bool:
        """
        Execute complete workflow for project.

        Returns:
            True if execution successful, False if failed
        """
        self.logger.info(f"Starting workflow execution for project: {self.project_id}")

        try:
            while True:
                # Check if needs human approval
                if not self.can_proceed():
                    self.logger.warning("Project requires human approval")
                    return False

                # Get next task
                task = self.get_next_task()
                if not task:
                    break  # All tasks completed

                # Execute task
                success = self.execute_task(task)

                if not success:
                    # Handle failure
                    task = TaskManager.load_task(self.project_id, task.task_id)
                    recovery = self.handle_task_failure(task)

                    if not recovery:
                        # Cannot recover
                        ProjectRegistry.update_project_status(
                            self.project_id,
                            ProjectStatus.FAILED,
                            error_message=f"Task {task.task_id} failed"
                        )
                        return False

            # All tasks completed
            self.logger.info("Workflow execution complete")
            ProjectRegistry.update_project_status(
                self.project_id,
                ProjectStatus.COMPLETE
            )

            return True

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            ProjectRegistry.update_project_status(
                self.project_id,
                ProjectStatus.FAILED,
                error_message=str(e)
            )
            return False

    def get_execution_report(self) -> Dict[str, Any]:
        """Get detailed execution report."""
        tasks = TaskManager.get_all_tasks(self.project_id)
        summary = TaskManager.get_task_status_summary(self.project_id)
        execution_time = TaskManager.get_execution_time(self.project_id)

        return {
            "project_id": self.project_id,
            "status": self.project_config.status.value,
            "phase": self.project_config.current_phase.value,
            "task_summary": summary,
            "total_execution_time_seconds": execution_time,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "agent_id": t.agent_id,
                    "status": t.status.value,
                    "attempts": t.attempts,
                    "duration_seconds": t.duration_seconds,
                    "errors": t.errors
                }
                for t in tasks
            ],
            "created_at": self.project_config.created_at.isoformat(),
            "completed_at": self.project_config.completed_at.isoformat() if self.project_config.completed_at else None
        }
