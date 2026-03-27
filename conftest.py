"""
Root-level pytest configuration and fixtures.

Provides:
- Pytest setup and configuration
- Shared fixtures for all tests
- Test utilities and helpers
- Factory patterns for test object creation (Quick Win 5)
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
import tempfile
import json
from pathlib import Path

from state_models import (
    AgentState,
    ProjectMetadata,
    PlanningArtifacts,
    ArchitectureArtifacts,
    DevelopmentArtifacts,
    DevelopmentSection,
    TestingArtifacts,
    DocumentationArtifacts,
    AgentMessage,
    TaskRecord,
    AgentPhase,
    TaskStatus,
    ExecutionStatus,
    create_initial_state,
)


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for component interactions"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests for complete workflows"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests that may take significant time"
    )


# ============================================================================
# Factory Classes for Test Object Creation (Quick Win 5)
# ============================================================================


class AgentStateFactory:
    """Factory for creating test AgentState objects."""

    @staticmethod
    def create_simple() -> AgentState:
        """Create simple initial state."""
        state = create_initial_state(
            project_id="test_simple_001",
            user_request="Simple test project"
        )
        return state

    @staticmethod
    def create_with_planning() -> AgentState:
        """Create state after planning phase."""
        state = AgentStateFactory.create_simple()
        state.planning_artifacts.requirements = "Test project requirements"
        state.planning_artifacts.tasks = [
            {"task_id": "T001", "title": "Design", "status": "completed"},
            {"task_id": "T002", "title": "Frontend", "status": "pending"},
        ]
        state.planning_artifacts.complexity_score = 45
        state.metadata.current_phase = AgentPhase.PLANNING
        return state

    @staticmethod
    def create_with_architecture() -> AgentState:
        """Create state after architecture phase."""
        state = AgentStateFactory.create_with_planning()
        state.architecture_artifacts.system_design = "Monolithic architecture"
        state.architecture_artifacts.component_specs = {
            "Dashboard": {
                "type": "React.FC",
                "props": ["data"]
            }
        }
        state.architecture_artifacts.api_specs = {
            "/api/data": {"method": "GET"}
        }
        state.metadata.current_phase = AgentPhase.ARCHITECTURE
        return state

    @staticmethod
    def create_full() -> AgentState:
        """Create state with all phases complete."""
        state = AgentStateFactory.create_with_architecture()
        state.development.frontend.code_files = {
            "src/App.tsx": "// React app"
        }
        state.development.backend.code_files = {
            "main.py": "# FastAPI app"
        }
        state.testing_artifacts.test_results = {
            "total": 10, "passed": 10, "failed": 0, "coverage": 85.0
        }
        state.documentation_artifacts.readme = "# Project README"
        state.metadata.current_phase = AgentPhase.COMPLETE
        return state

    @staticmethod
    def create_complex() -> AgentState:
        """Create state for complex project."""
        state = create_initial_state(
            project_id="test_complex_001",
            user_request="Build a comprehensive e-commerce platform with React, FastAPI, PostgreSQL, Redis, authentication, payments, and admin dashboard"
        )
        state.planning_artifacts.complexity_score = 85
        state.planning_artifacts.complexity_factors = [
            "api", "database_heavy", "requires_auth", "requires_payment",
            "ui_heavy", "requires_scalability"
        ]
        return state


# ============================================================================
# Temporary Directory Fixture
# ============================================================================

@pytest.fixture
def tmp_workspace(tmp_path):
    """Provide a temporary workspace directory with standard structure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)

    # Create standard directories
    (workspace / "checkpoints").mkdir(exist_ok=True)
    (workspace / "generated").mkdir(exist_ok=True)
    (workspace / "generated" / "frontend").mkdir(exist_ok=True)
    (workspace / "generated" / "backend").mkdir(exist_ok=True)
    (workspace / "generated" / "docs").mkdir(exist_ok=True)
    (workspace / "artifacts").mkdir(exist_ok=True)

    return workspace


# ============================================================================
# State Fixtures
# ============================================================================

@pytest.fixture
def simple_project_state():
    """Create a simple project state (todo app)."""
    state = create_initial_state(
        project_id="simple_todo_001",
        user_request="Build a simple todo list application",
        tech_stack={"frontend": "React", "backend": "FastAPI"}
    )
    return state


@pytest.fixture
def complex_project_state():
    """Create a complex project state (e-commerce platform)."""
    state = create_initial_state(
        project_id="ecom_platform_001",
        user_request=(
            "Build a full-stack e-commerce platform with user authentication, "
            "product catalog, shopping cart, payment processing, and admin dashboard"
        ),
        tech_stack={"frontend": "React", "backend": "FastAPI", "database": "PostgreSQL"}
    )
    state.planning_artifacts.complexity_score = 85
    state.planning_artifacts.complexity_factors = [
        "api", "database_heavy", "requires_auth", "requires_compliance",
        "ui_heavy", "requires_scalability", "sensitive_data_types"
    ]
    return state


@pytest.fixture
def planning_phase_state(simple_project_state):
    """Create state after planning phase."""
    state = simple_project_state
    state.planning_artifacts.requirements = (
        "Build a todo app with CRUD operations and user authentication"
    )
    state.planning_artifacts.tasks = [
        {"task_id": "T001", "title": "Design architecture", "status": "pending"},
        {"task_id": "T002", "title": "Create frontend components", "status": "pending"},
        {"task_id": "T003", "title": "Create API endpoints", "status": "pending"},
    ]
    state.planning_artifacts.dependencies = {
        "T002": ["T001"],
        "T003": ["T001"]
    }
    state.planning_artifacts.risks = ["Authentication complexity", "Database scaling"]
    state.metadata.current_phase = AgentPhase.PLANNING
    return state


@pytest.fixture
def architecture_phase_state(planning_phase_state):
    """Create state after architecture phase."""
    from artifact_schemas import ComponentSpec, APIEndpoint

    state = planning_phase_state
    state.architecture_artifacts.system_design = (
        "Monolithic architecture with React frontend and FastAPI backend"
    )
    state.architecture_artifacts.component_specs = {
        "TodoList": ComponentSpec(
            name="TodoList",
            description="Renders the todo list",
            props={"todos": "list", "onAdd": "callable", "onDelete": "callable"},
            state=["todos"],
        ),
        "TodoItem": ComponentSpec(
            name="TodoItem",
            description="Renders a single todo",
            props={"todo": "dict", "onDelete": "callable"},
            state=[],
        ),
    }
    state.architecture_artifacts.api_specs = {
        "/api/todos-get": APIEndpoint(
            path="/api/todos",
            method="GET",
            description="Return all todos",
            response_schema={"todos": "array"},
        ),
        "/api/todos-post": APIEndpoint(
            path="/api/todos",
            method="POST",
            description="Create a new todo",
            request_schema={"title": "string"},
            response_schema={"id": "string", "title": "string"},
        ),
    }
    state.architecture_artifacts.database_schema = (
        "todos table with id, title, completed, user_id"
    )
    state.metadata.current_phase = AgentPhase.ARCHITECTURE
    return state



# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def sample_code_files() -> Dict[str, str]:
    """Create sample code files."""
    return {
        "frontend/src/components/TodoList.tsx": """
import React from 'react';

export const TodoList: React.FC = () => {
  return <div>Todo List</div>;
};
""",
        "backend/main.py": """
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/todos")
def get_todos():
    return []
""",
    }


@pytest.fixture
def sample_test_results() -> Dict[str, Any]:
    """Create sample test results."""
    return {
        "total": 45,
        "passed": 42,
        "failed": 3,
        "skipped": 0,
        "coverage": 78.5,
        "execution_time_seconds": 12.3,
    }


@pytest.fixture
def sample_artifacts() -> Dict[str, Any]:
    """Create sample artifacts for complete workflow."""
    return {
        "planning": {
            "requirements": "Build a todo app",
            "tasks": [
                {"task_id": "T001", "title": "Design", "status": "completed"},
            ],
            "dependencies": {},
            "complexity_score": 35,
        },
        "architecture": {
            "system_design": "Monolithic app",
            "component_specs": {
                "TodoList": {
                    "type": "React.FC",
                    "props": ["todos"],
                }
            },
            "api_specs": {
                "/api/todos": {"method": "GET"}
            },
        },
        "frontend": {
            "code_files": {
                "src/components/TodoList.tsx": "// React component"
            },
        },
        "backend": {
            "code_files": {
                "main.py": "# FastAPI app"
            },
        },
    }


# ============================================================================
# State Validation Helpers
# ============================================================================

@pytest.fixture
def state_validator():
    """Provide state validation utilities."""
    class StateValidator:
        @staticmethod
        def validate_structure(state: AgentState) -> List[str]:
            """Validate state structure, return list of errors."""
            errors = []

            if not state.metadata.project_id:
                errors.append("metadata.project_id is empty")

            if not state.metadata.user_request:
                errors.append("metadata.user_request is empty")

            if not isinstance(state.planning_artifacts, PlanningArtifacts):
                errors.append("planning_artifacts is not PlanningArtifacts type")

            if not isinstance(state.architecture_artifacts, ArchitectureArtifacts):
                errors.append("architecture_artifacts is not ArchitectureArtifacts type")

            if not isinstance(state.development, DevelopmentSection):
                errors.append("development is not DevelopmentSection type")

            if not isinstance(state.testing_artifacts, TestingArtifacts):
                errors.append("testing_artifacts is not TestingArtifacts type")

            if not isinstance(state.documentation_artifacts, DocumentationArtifacts):
                errors.append("documentation_artifacts is not DocumentationArtifacts type")

            return errors

        @staticmethod
        def validate_phase_transition(
            old_phase: AgentPhase,
            new_phase: AgentPhase
        ) -> bool:
            """Validate phase transition is valid."""
            valid_transitions = {
                AgentPhase.PLANNING: [AgentPhase.ARCHITECTURE],
                AgentPhase.ARCHITECTURE: [AgentPhase.CONTRACT_VALIDATION, AgentPhase.FRONTEND, AgentPhase.BACKEND],
                AgentPhase.CONTRACT_VALIDATION: [AgentPhase.FRONTEND, AgentPhase.BACKEND],
                AgentPhase.FRONTEND: [AgentPhase.QA],
                AgentPhase.BACKEND: [AgentPhase.QA],
                AgentPhase.QA: [AgentPhase.DOCUMENTATION, AgentPhase.FRONTEND, AgentPhase.BACKEND],
                AgentPhase.DOCUMENTATION: [AgentPhase.COMPLETE],
                AgentPhase.COMPLETE: [],
            }
            return new_phase in valid_transitions.get(old_phase, [])

        @staticmethod
        def count_artifacts(state: AgentState) -> Dict[str, int]:
            """Count artifacts in each section."""
            return {
                "planning": len([x for x in [state.planning_artifacts.requirements] if x]),
                "architecture": (
                    len(state.architecture_artifacts.component_specs) +
                    len(state.architecture_artifacts.api_specs)
                ),
                "frontend_code": len(state.development.frontend.code_files),
                "backend_code": len(state.development.backend.code_files),
                "tests": len(state.testing_artifacts.bug_reports),
            }

    return StateValidator()


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Automatically cleanup temporary files after each test."""
    yield
    # Cleanup happens automatically with tmp_path fixture


@pytest.fixture
def isolated_project_state(tmp_workspace):
    """Create an isolated project state with temporary workspace."""
    state = create_initial_state(
        project_id="isolated_test_001",
        user_request="Test project"
    )
    state._workspace = tmp_workspace
    return state


# ============================================================================
# Factory Fixtures (Quick Win 5)
# ============================================================================

@pytest.fixture
def project_config_factory():
    """Provide ProjectConfigFactory for tests."""
    ProjectConfigFactory.reset()
    return ProjectConfigFactory


@pytest.fixture
def agent_state_factory():
    """Provide AgentStateFactory for tests."""
    return AgentStateFactory
