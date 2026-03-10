"""
Phase 2 tests: Orchestrator and project isolation.

Tests validate:
1. Project registry (create, load, save)
2. Team registry (create universal team, load)
3. Task management (create, track, update)
4. Orchestrator initialization and execution
"""

import pytest
import tempfile
import json
import shutil
from pathlib import Path
from datetime import datetime

# Mock the home directory for testing
import os
os.environ["HOME"] = tempfile.mkdtemp()

from orchestrator.project_registry import ProjectRegistry, ProjectConfig, ProjectStatus, ProjectPhase
from orchestrator.team_registry import TeamRegistry, TeamConfig
from orchestrator.task_manager import TaskManager, TaskRecord, TaskStatus
from orchestrator.orchestrator import ProjectOrchestrator, OrchestratorConfig


# ============================================================================
# Project Registry Tests
# ============================================================================

class TestProjectRegistry:
    """Test project registry functionality."""

    def test_create_project(self):
        """Test creating a new project."""
        config = ProjectRegistry.create_project(
            project_id="test-project-1",
            user_request="Build a test app"
        )

        assert config.project_id == "test-project-1"
        assert config.user_request == "Build a test app"
        assert config.status == ProjectStatus.PENDING
        assert ProjectRegistry.project_exists("test-project-1")

    def test_save_and_load_project(self):
        """Test saving and loading project config."""
        config = ProjectRegistry.create_project(
            project_id="test-project-2",
            user_request="Test request",
            team_id="universal-agents-v1"
        )

        # Load it back
        loaded = ProjectRegistry.load_project_config("test-project-2")

        assert loaded is not None
        assert loaded.project_id == config.project_id
        assert loaded.user_request == config.user_request
        assert loaded.team_id == config.team_id

    def test_update_project_phase(self):
        """Test updating project phase."""
        ProjectRegistry.create_project(
            project_id="test-project-3",
            user_request="Test project"
        )

        ProjectRegistry.update_project_phase(
            "test-project-3",
            ProjectPhase.ARCHITECTURE
        )

        config = ProjectRegistry.load_project_config("test-project-3")
        assert config.current_phase == ProjectPhase.ARCHITECTURE

    def test_update_project_status(self):
        """Test updating project status."""
        ProjectRegistry.create_project(
            project_id="test-project-4",
            user_request="Test project"
        )

        ProjectRegistry.update_project_status(
            "test-project-4",
            ProjectStatus.IN_PROGRESS
        )

        config = ProjectRegistry.load_project_config("test-project-4")
        assert config.status == ProjectStatus.IN_PROGRESS
        assert config.started_at is not None

    def test_set_human_approval(self):
        """Test setting human approval requirement."""
        ProjectRegistry.create_project(
            project_id="test-project-5",
            user_request="Test project"
        )

        ProjectRegistry.set_human_approval_needed(
            "test-project-5",
            "Needs clarification"
        )

        config = ProjectRegistry.load_project_config("test-project-5")
        assert config.requires_human_approval is True
        assert config.approval_reason == "Needs clarification"
        assert config.status == ProjectStatus.PAUSED

    def test_get_all_projects(self):
        """Test getting all projects."""
        # Create multiple projects
        for i in range(3):
            ProjectRegistry.create_project(
                project_id=f"test-project-{100+i}",
                user_request=f"Test project {i}"
            )

        all_projects = ProjectRegistry.get_all_projects()
        assert len(all_projects) >= 3

    def test_project_summary(self):
        """Test getting project summary."""
        ProjectRegistry.create_project(
            project_id="test-project-summary",
            user_request="Test project"
        )

        summary = ProjectRegistry.get_project_summary("test-project-summary")
        assert summary["project_id"] == "test-project-summary"
        assert summary["status"] == "pending"


# ============================================================================
# Team Registry Tests
# ============================================================================

class TestTeamRegistry:
    """Test team registry functionality."""

    def test_create_universal_team(self):
        """Test creating universal team."""
        team = TeamRegistry.create_universal_team()

        assert team.team_id == "universal-agents-v1"
        assert len(team.agents) == 7  # 7 agents in universal team
        assert TeamRegistry.team_exists("universal-agents-v1")

    def test_load_universal_team(self):
        """Test loading universal team."""
        TeamRegistry.create_universal_team()

        team = TeamRegistry.load_team_config("universal-agents-v1")
        assert team is not None
        assert team.team_id == "universal-agents-v1"

    def test_team_dependencies(self):
        """Test getting team dependencies."""
        TeamRegistry.create_universal_team()

        deps = TeamRegistry.get_team_dependencies("universal-agents-v1")
        assert deps is not None
        assert "planning" in deps
        assert "architecture" in deps
        assert deps["planning"] == []  # Planning has no dependencies
        assert "architecture" in deps["frontend"]  # Frontend depends on architecture

    def test_get_agent_spec(self):
        """Test getting agent spec."""
        TeamRegistry.create_universal_team()

        spec = TeamRegistry.get_agent_spec("universal-agents-v1", "planning")
        assert spec is not None
        assert spec.agent_id == "planning"
        assert spec.role == "planning"

    def test_ensure_universal_team(self):
        """Test ensuring universal team exists."""
        # Delete team if it exists
        team_dir = TeamRegistry.get_team_dir("universal-agents-v1")
        if team_dir.exists():
            shutil.rmtree(team_dir)

        # Ensure it gets created
        TeamRegistry.ensure_universal_team()
        assert TeamRegistry.team_exists("universal-agents-v1")


# ============================================================================
# Task Manager Tests
# ============================================================================

class TestTaskManager:
    """Test task management functionality."""

    def setup_method(self):
        """Setup for each test."""
        self.project_id = "test-task-project"
        # Clean up existing tasks to ensure test isolation
        tasks_dir = TaskManager.get_all_tasks_dir(self.project_id)
        if tasks_dir.exists():
            shutil.rmtree(tasks_dir)
        ProjectRegistry.create_project(
            project_id=self.project_id,
            user_request="Test project"
        )

    def test_create_tasks(self):
        """Test creating tasks for a project."""
        dependencies = {
            "planning": [],
            "architecture": ["planning"],
            "frontend": ["architecture"],
            "backend": ["architecture"],
            "qa": ["frontend", "backend"],
            "documentation": ["qa"]
        }

        tasks = TaskManager.create_tasks_for_project(self.project_id, dependencies)

        assert len(tasks) == 6
        assert all(isinstance(t, TaskRecord) for t in tasks)

    def test_save_and_load_task(self):
        """Test saving and loading tasks."""
        task = TaskRecord(
            task_id="test-task-1",
            project_id=self.project_id,
            agent_id="planning",
            phase="planning"
        )

        TaskManager.save_task(task, self.project_id)
        loaded = TaskManager.load_task(self.project_id, "test-task-1")

        assert loaded is not None
        assert loaded.task_id == task.task_id
        assert loaded.agent_id == task.agent_id

    def test_get_all_tasks(self):
        """Test getting all tasks."""
        dependencies = {
            "planning": [],
            "architecture": ["planning"],
            "qa": ["architecture"]
        }

        TaskManager.create_tasks_for_project(self.project_id, dependencies)
        all_tasks = TaskManager.get_all_tasks(self.project_id)

        assert len(all_tasks) == 3

    def test_update_task_status(self):
        """Test updating task status."""
        task = TaskRecord(
            task_id="test-task-2",
            project_id=self.project_id,
            agent_id="planning",
            phase="planning"
        )
        TaskManager.save_task(task, self.project_id)

        TaskManager.update_task_status(
            self.project_id,
            "test-task-2",
            TaskStatus.COMPLETED
        )

        updated = TaskManager.load_task(self.project_id, "test-task-2")
        assert updated.status == TaskStatus.COMPLETED
        assert updated.completed_at is not None

    def test_get_ready_tasks(self):
        """Test getting ready tasks (no blocking dependencies)."""
        # Create task with dependency
        planning_task = TaskRecord(
            task_id="planning-task",
            project_id=self.project_id,
            agent_id="planning",
            phase="planning",
            depends_on=[]
        )

        arch_task = TaskRecord(
            task_id="arch-task",
            project_id=self.project_id,
            agent_id="architecture",
            phase="architecture",
            depends_on=["planning-task"]
        )

        TaskManager.save_task(planning_task, self.project_id)
        TaskManager.save_task(arch_task, self.project_id)

        # Only planning should be ready
        ready = TaskManager.get_ready_tasks(self.project_id)
        assert len(ready) == 1
        assert ready[0].agent_id == "planning"

        # After planning completes, architecture should be ready
        TaskManager.update_task_status(
            self.project_id,
            "planning-task",
            TaskStatus.COMPLETED
        )

        ready = TaskManager.get_ready_tasks(self.project_id)
        assert len(ready) == 1
        assert ready[0].agent_id == "architecture"

    def test_get_next_task(self):
        """Test getting next task."""
        planning_task = TaskRecord(
            task_id="planning",
            project_id=self.project_id,
            agent_id="planning",
            phase="planning"
        )
        TaskManager.save_task(planning_task, self.project_id)

        next_task = TaskManager.get_next_task(self.project_id)
        assert next_task is not None
        assert next_task.agent_id == "planning"

    def test_task_status_summary(self):
        """Test getting task status summary."""
        for i in range(3):
            task = TaskRecord(
                task_id=f"task-{i}",
                project_id=self.project_id,
                agent_id=f"agent-{i}",
                phase="test",
                status=TaskStatus.PENDING if i == 0 else TaskStatus.COMPLETED
            )
            TaskManager.save_task(task, self.project_id)

        summary = TaskManager.get_task_status_summary(self.project_id)
        assert summary["total"] == 3
        assert summary["pending"] == 1
        assert summary["completed"] == 2


# ============================================================================
# Orchestrator Tests
# ============================================================================

class TestProjectOrchestrator:
    """Test ProjectOrchestrator functionality."""

    def setup_method(self):
        """Setup for each test."""
        # Ensure universal team exists
        TeamRegistry.ensure_universal_team()

        # Create a test project
        self.project_id = "test-orchestrator-project"
        ProjectRegistry.create_project(
            project_id=self.project_id,
            user_request="Build a test application"
        )

    def test_orchestrator_initialization(self):
        """Test initializing orchestrator."""
        orchestrator = ProjectOrchestrator(self.project_id)

        assert orchestrator.project_id == self.project_id
        assert orchestrator.project_config is not None
        assert orchestrator.team_config is not None
        assert orchestrator.state is not None

    def test_get_current_status(self):
        """Test getting orchestrator status."""
        orchestrator = ProjectOrchestrator(self.project_id)
        status = orchestrator.get_current_status()

        assert status["project_id"] == self.project_id
        assert "task_summary" in status
        assert status["task_summary"]["total"] > 0

    def test_get_next_task(self):
        """Test getting next task from orchestrator."""
        orchestrator = ProjectOrchestrator(self.project_id)
        next_task = orchestrator.get_next_task()

        assert next_task is not None
        # First task should be planning (no dependencies)
        assert next_task.agent_id == "planning"

    def test_can_proceed(self):
        """Test checking if orchestrator can proceed."""
        orchestrator = ProjectOrchestrator(self.project_id)
        assert orchestrator.can_proceed() is True

        # Set human approval needed
        ProjectRegistry.set_human_approval_needed(self.project_id, "Test reason")
        orchestrator = ProjectOrchestrator(self.project_id)
        assert orchestrator.can_proceed() is False

    def test_get_execution_report(self):
        """Test getting execution report."""
        orchestrator = ProjectOrchestrator(self.project_id)
        report = orchestrator.get_execution_report()

        assert report["project_id"] == self.project_id
        assert "task_summary" in report
        assert "tasks" in report
        assert len(report["tasks"]) > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestPhase2Integration:
    """Integration tests for Phase 2."""

    def test_project_lifecycle(self):
        """Test complete project lifecycle."""
        # Create project
        project_id = "integration-test-project"
        ProjectRegistry.create_project(
            project_id=project_id,
            user_request="Integration test"
        )

        # Ensure team exists
        TeamRegistry.ensure_universal_team()

        # Initialize orchestrator
        orchestrator = ProjectOrchestrator(project_id)

        # Verify initial state
        assert orchestrator.project_config.status == ProjectStatus.PENDING
        status = orchestrator.get_current_status()
        assert status["task_summary"]["total"] > 0
        assert status["task_summary"]["pending"] > 0

        # Mark first task as completed
        first_task = orchestrator.get_next_task()
        assert first_task is not None

        TaskManager.update_task_status(
            project_id,
            first_task.task_id,
            TaskStatus.COMPLETED
        )

        # Second task should now be ready
        orchestrator = ProjectOrchestrator(project_id)
        next_task = orchestrator.get_next_task()
        assert next_task is not None
        assert next_task.task_id != first_task.task_id

    def test_teams_and_projects_isolation(self):
        """Test that teams and projects are properly isolated."""
        # Create two projects with same team
        project1_id = "iso-test-project-1"
        project2_id = "iso-test-project-2"

        ProjectRegistry.create_project(project1_id, "Test 1")
        ProjectRegistry.create_project(project2_id, "Test 2")

        TeamRegistry.ensure_universal_team()

        # Initialize both orchestrators
        orchestrator1 = ProjectOrchestrator(project1_id)
        orchestrator2 = ProjectOrchestrator(project2_id)

        # They should share the same team config but have different project configs
        assert orchestrator1.team_config.team_id == orchestrator2.team_config.team_id
        assert orchestrator1.project_config.project_id != orchestrator2.project_config.project_id

        # Tasks should be separate
        task1 = TaskManager.get_all_tasks(project1_id)
        task2 = TaskManager.get_all_tasks(project2_id)

        assert len(task1) > 0
        assert len(task2) > 0
        assert task1[0].project_id != task2[0].project_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
