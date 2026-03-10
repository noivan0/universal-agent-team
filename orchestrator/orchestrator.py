"""
ProjectOrchestrator: Main orchestration engine for multi-agent workflows.

Coordinates agent execution, manages state, handles errors, and enables
intelligent restart planning based on failures.
"""

import logging
import concurrent.futures
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from state_models import AgentState, AgentError, ErrorType, create_initial_state, apply_state_update
from dependency_context import DependencyContextLoader, RestartImpactAnalyzer
from checkpoint_manager import CheckpointManager, StreamingExecutionHandler
from agent_validators import AgentOutputValidator
from agent_executor import execute_agent

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
        """Load existing state from disk or create new one.

        Attempts to restore the last saved state from current_state.json.
        If the file is missing, corrupt, or schema-incompatible, falls back
        to creating a fresh state so the workflow can always start.
        """
        state_file = ProjectRegistry.get_state_dir(self.project_id) / "current_state.json"

        if state_file.exists():
            self.logger.info(f"Loading existing project state from {state_file}")
            try:
                import json as _json
                with open(state_file) as f:
                    data = _json.load(f)
                from checkpoint_manager import migrate_state
                data = migrate_state(data)
                state = AgentState(**data)
                self.logger.info(
                    f"Restored state: phase={state.metadata.current_phase.value}, "
                    f"messages={len(state.messages)}, "
                    f"complete={state.is_complete}"
                )
                return state
            except Exception as exc:
                self.logger.warning(
                    f"Failed to load state from {state_file}: {exc}. "
                    "Creating fresh state instead."
                )

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
            # ── Real LLM agent execution ──────────────────────────────────
            self.logger.info(f"Invoking agent '{task.agent_id}' via LLM")
            state_update = execute_agent(task.agent_id, self.state)

            # Validate the structured output before applying it
            output_dict = {}
            if state_update.planning_artifacts:
                output_dict = state_update.planning_artifacts.model_dump()
            elif state_update.architecture_artifacts:
                output_dict = state_update.architecture_artifacts.model_dump()
            elif state_update.development:
                # For dev agents, check whichever section was filled
                fe = state_update.development.frontend
                be = state_update.development.backend
                if fe.code_files:
                    output_dict = {"code_files": fe.code_files}
                elif be.code_files:
                    output_dict = {"code_files": be.code_files}
            elif state_update.testing_artifacts:
                output_dict = state_update.testing_artifacts.model_dump()
            elif state_update.documentation_artifacts:
                output_dict = {"readme": state_update.documentation_artifacts.readme}

            validation = AgentOutputValidator.validate(task.agent_id, output_dict, self.state)
            for issue in validation.issues:
                level = self.logger.warning if issue.blocking else self.logger.debug
                level(f"[{task.task_id}] {issue.field}: {issue.message}")

            if validation.has_blocking_issues:
                raise ValueError(
                    f"Output validation failed for '{task.agent_id}': "
                    + "; ".join(i.message for i in validation.blocking_issues)
                )

            # Apply state update
            self.state = apply_state_update(self.state, state_update)

            # Save checkpoint after successful execution
            handler = StreamingExecutionHandler(self.project_id, task.agent_id)
            handler.create_checkpoint(self.state, progress=100, is_complete=True)

            TaskManager.update_task_status(self.project_id, task.task_id, TaskStatus.COMPLETED)
            self.logger.info(f"Task {task.task_id} completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Task {task.task_id} failed: {e}")
            TaskManager.update_task_status(
                self.project_id,
                task.task_id,
                TaskStatus.FAILED,
                error=str(e)
            )

            # Record structured error in state
            self.state.add_error(AgentError(
                agent_id=task.agent_id,
                error_type=self._classify_error_message(str(e)),
                message=str(e),
                suggested_fix="Check agent output format or retry with simplified prompt"
            ))

            # Mark downstream tasks as blocked
            TaskManager.mark_blocked_downstream(self.project_id, task.task_id)
            return False

    def _classify_error_message(self, error_msg: str) -> ErrorType:
        """
        Classify an error message string into an ErrorType for routing decisions.

        Returns:
            ErrorType enum value for the given error message
        """
        msg = error_msg.lower()

        # Deterministic: same error repeated across attempts
        # (checked via task record comparison in handle_task_failure)
        if "timeout" in msg or "rate limit" in msg or "connection" in msg or "503" in msg:
            return ErrorType.TRANSIENT
        if "parse" in msg or "json" in msg or "format" in msg or "decode" in msg:
            return ErrorType.PARSE_ERROR
        if "validation" in msg or "invalid" in msg or "schema" in msg:
            return ErrorType.VALIDATION_ERROR
        return ErrorType.UNKNOWN

    def handle_task_failure(self, task: TaskRecord) -> bool:
        """
        Handle task failure with intelligent error classification.

        Classifies the error type before deciding whether to retry or escalate:
        - DETERMINISTIC → escalate immediately (same error repeating, retrying wastes quota)
        - TRANSIENT / PARSE_ERROR / VALIDATION_ERROR / UNKNOWN → retry up to max_attempts

        Args:
            task: Failed task record (freshly loaded from disk)

        Returns:
            True if retry was scheduled, False if escalation is required
        """
        self.logger.warning(f"Handling failure for task: {task.task_id}")

        # Classify using the last recorded error
        last_error = task.errors[-1] if task.errors else ""
        error_type = self._classify_error_message(last_error)

        # Detect deterministic failures: same error message on consecutive attempts
        if (
            error_type == ErrorType.DETERMINISTIC
            or (len(task.errors) >= 2 and task.errors[-1] == task.errors[-2])
        ):
            self.logger.error(
                f"Deterministic failure detected for task {task.task_id} — escalating to human review"
            )
            self.state.add_error(AgentError(
                agent_id=task.agent_id,
                error_type=ErrorType.DETERMINISTIC,
                message=last_error,
                suggested_fix="Manual intervention required — the agent produces the same error repeatedly"
            ))
            ProjectRegistry.set_human_approval_needed(
                self.project_id,
                f"Task {task.task_id} has a deterministic failure: {last_error}"
            )
            return False

        if TaskManager.can_retry_task(self.project_id, task.task_id):
            self.logger.info(
                f"Retrying task {task.task_id} "
                f"(attempt {task.attempts + 1}/{task.max_attempts}, "
                f"error_type={error_type.value})"
            )
            TaskManager.reset_task_for_retry(self.project_id, task.task_id)
            return True

        self.logger.error(f"Max retries exceeded for task: {task.task_id}")
        ProjectRegistry.set_human_approval_needed(
            self.project_id,
            f"Task {task.task_id} failed after {task.max_attempts} attempts"
        )
        return False

    def execute_tasks_parallel(
        self, tasks: List[TaskRecord]
    ) -> List[Tuple[TaskRecord, bool]]:
        """
        Execute multiple dependency-unblocked tasks concurrently.

        Each task runs in its own thread. Results are collected once all
        threads finish (fan-out / fan-in pattern).

        Args:
            tasks: List of ready TaskRecord objects to run in parallel

        Returns:
            List of (task, success) tuples in completion order
        """
        self.logger.info(
            f"Parallel execution: {len(tasks)} tasks "
            f"[{', '.join(t.task_id for t in tasks)}]"
        )

        results: List[Tuple[TaskRecord, bool]] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            future_to_task = {
                executor.submit(self.execute_task, task): task
                for task in tasks
            }

            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    success = future.result()
                except Exception as exc:
                    self.logger.error(f"Task {task.task_id} raised unhandled exception: {exc}")
                    success = False
                results.append((task, success))

        return results

    def execute_workflow(self) -> bool:
        """
        Execute the complete workflow with parallel task execution.

        In each iteration of the loop all dependency-unblocked tasks are
        collected. If more than one is ready *and* parallel_execution is
        enabled they run concurrently via ThreadPoolExecutor; otherwise they
        run sequentially. This correctly handles stages like
        Frontend + Backend that share no dependency and can run at the same
        time.

        Returns:
            True if all tasks completed successfully, False on failure
        """
        self.logger.info(f"Starting workflow execution for project: {self.project_id}")

        try:
            while True:
                if not self.can_proceed():
                    self.logger.warning("Project requires human approval — pausing workflow")
                    return False

                ready_tasks = TaskManager.get_ready_tasks(self.project_id)

                if not ready_tasks:
                    # Nothing is ready — check overall state
                    all_tasks = TaskManager.get_all_tasks(self.project_id)
                    if not all_tasks:
                        break  # No tasks at all (empty project)

                    completed = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
                    if len(completed) == len(all_tasks):
                        break  # Every task is done

                    # Some tasks may be BLOCKED or FAILED with no ready successors
                    failed = [t for t in all_tasks if t.status == TaskStatus.FAILED]
                    if failed:
                        self.logger.error(
                            f"Workflow stalled — {len(failed)} failed tasks with no ready successors"
                        )
                        ProjectRegistry.update_project_status(
                            self.project_id,
                            ProjectStatus.FAILED,
                            error_message=f"Tasks failed: {[t.task_id for t in failed]}"
                        )
                        return False

                    break  # Nothing more to do

                # ── Single task: run directly to avoid thread overhead ──
                if len(ready_tasks) == 1 or not self.config.parallel_execution:
                    for task in ready_tasks:
                        success = self.execute_task(task)
                        if not success:
                            fresh_task = TaskManager.load_task(self.project_id, task.task_id)
                            recovery = self.handle_task_failure(fresh_task)
                            if not recovery:
                                ProjectRegistry.update_project_status(
                                    self.project_id,
                                    ProjectStatus.FAILED,
                                    error_message=f"Task {task.task_id} failed"
                                )
                                return False

                # ── Multiple ready tasks: execute in parallel ──
                else:
                    pair_results = self.execute_tasks_parallel(ready_tasks)
                    for task, success in pair_results:
                        if not success:
                            fresh_task = TaskManager.load_task(self.project_id, task.task_id)
                            recovery = self.handle_task_failure(fresh_task)
                            if not recovery:
                                ProjectRegistry.update_project_status(
                                    self.project_id,
                                    ProjectStatus.FAILED,
                                    error_message=f"Task {task.task_id} failed"
                                )
                                return False

            self.logger.info("Workflow execution complete")
            ProjectRegistry.update_project_status(self.project_id, ProjectStatus.COMPLETE)
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
