"""
Unit tests for state models.

Tests cover:
- AgentState hierarchical structure
- Artifact sections (planning, architecture, development, testing, documentation)
- Version tracking and execution status
- Pydantic validation
- State transitions and convenience methods
"""

import pytest
from datetime import datetime
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
    ArtifactMetadata,
    ArtifactManifest,
    TaskRecord,
    AgentPhase,
    TaskStatus,
    ExecutionStatus,
    AgentExecutionStatus,
    ExecutionStatusTracker,
    CompressionStats,
    create_initial_state,
    apply_state_update,
    StateUpdate,
)


@pytest.mark.unit
class TestAgentStateStructure:
    """Test AgentState hierarchical structure."""

    def test_create_initial_state(self):
        """Test creating an initial agent state."""
        state = create_initial_state(
            project_id="test_001",
            user_request="Build a todo app",
            tech_stack={"frontend": "React", "backend": "FastAPI"}
        )

        assert state.metadata.project_id == "test_001"
        assert state.metadata.user_request == "Build a todo app"
        assert state.metadata.tech_stack["frontend"] == "React"
        assert state.metadata.current_phase == AgentPhase.PLANNING
        assert isinstance(state.planning_artifacts, PlanningArtifacts)
        assert isinstance(state.architecture_artifacts, ArchitectureArtifacts)
        assert isinstance(state.development, DevelopmentSection)

    def test_state_has_all_sections(self):
        """Test that state has all required artifact sections."""
        state = create_initial_state("test_001", "Test request")

        assert hasattr(state, "metadata")
        assert hasattr(state, "planning_artifacts")
        assert hasattr(state, "architecture_artifacts")
        assert hasattr(state, "development")
        assert hasattr(state, "testing_artifacts")
        assert hasattr(state, "documentation_artifacts")
        assert hasattr(state, "execution_status")
        assert hasattr(state, "messages")
        assert hasattr(state, "errors")

    def test_state_isolation_sections(self):
        """Test that state sections are properly isolated."""
        state1 = create_initial_state("proj1", "Request 1")
        state2 = create_initial_state("proj2", "Request 2")

        # Modify state1's planning artifacts
        state1.planning_artifacts.requirements = "Modified requirements"

        # state2 should be unaffected
        assert state2.planning_artifacts.requirements is None
        assert state1.planning_artifacts.requirements == "Modified requirements"

    def test_state_serialization(self):
        """Test that state can be serialized and deserialized."""
        state = create_initial_state("test_001", "Build todo app")
        state.planning_artifacts.requirements = "Test requirements"

        # Serialize
        state_dict = state.model_dump()

        # Deserialize
        restored = AgentState(**state_dict)

        assert restored.metadata.project_id == "test_001"
        assert restored.planning_artifacts.requirements == "Test requirements"

    def test_state_json_encoding(self):
        """Test JSON encoding of state with datetime objects."""
        state = create_initial_state("test_001", "Build app")

        # Should not raise an exception
        json_str = state.model_dump_json()
        assert "test_001" in json_str
        assert isinstance(json_str, str)


@pytest.mark.unit
class TestPlanningArtifacts:
    """Test Planning Agent artifacts."""

    def test_planning_artifacts_initialization(self):
        """Test PlanningArtifacts initialization."""
        artifacts = PlanningArtifacts()

        assert artifacts.requirements is None
        assert artifacts.tasks == []
        assert artifacts.dependencies == {}
        assert artifacts.risks == []
        assert artifacts.complexity_score == 50
        assert len(artifacts.complexity_factors) == 0

    def test_planning_artifacts_with_data(self):
        """Test PlanningArtifacts with populated data."""
        artifacts = PlanningArtifacts(
            requirements="Build a todo app with authentication",
            complexity_score=65,
            complexity_factors=["api", "auth", "database"]
        )

        assert artifacts.requirements == "Build a todo app with authentication"
        assert artifacts.complexity_score == 65
        assert len(artifacts.complexity_factors) == 3

    def test_planning_tasks_structure(self):
        """Test task structure in planning artifacts."""
        artifacts = PlanningArtifacts()
        artifacts.tasks = [
            {"task_id": "T001", "title": "Design architecture", "status": "pending"},
            {"task_id": "T002", "title": "Implement frontend", "status": "pending"},
        ]

        assert len(artifacts.tasks) == 2
        assert artifacts.tasks[0]["task_id"] == "T001"

    def test_planning_tech_stack(self):
        """Test technology stack tracking in planning."""
        artifacts = PlanningArtifacts(
            tech_stack={"frontend": "React", "backend": "FastAPI", "database": "PostgreSQL"}
        )

        assert artifacts.tech_stack["frontend"] == "React"
        assert artifacts.tech_stack["backend"] == "FastAPI"


@pytest.mark.unit
class TestArchitectureArtifacts:
    """Test Architecture Agent artifacts."""

    def test_architecture_artifacts_initialization(self):
        """Test ArchitectureArtifacts initialization."""
        artifacts = ArchitectureArtifacts()

        assert artifacts.system_design is None
        assert artifacts.component_specs == {}
        assert artifacts.api_specs == {}
        assert artifacts.database_schema is None

    def test_component_specifications(self):
        """Test component specifications in architecture."""
        from artifact_schemas import ComponentSpec

        artifacts = ArchitectureArtifacts()
        artifacts.component_specs = {
            "UserDashboard": ComponentSpec(
                name="UserDashboard",
                description="Main user dashboard",
                props={"userId": "str", "onUpdate": "callable"},
                state=["loading", "userData"],
                api_calls=["/api/users/{id}"],
            ),
            "TodoList": ComponentSpec(
                name="TodoList",
                description="Renders list of todos",
                props={"todos": "list", "onAdd": "callable"},
                state=["todos"],
                api_calls=["/api/todos"],
            ),
        }

        assert len(artifacts.component_specs) == 2
        assert artifacts.component_specs["UserDashboard"].name == "UserDashboard"

    def test_api_specifications(self):
        """Test API specifications in architecture."""
        from artifact_schemas import APIEndpoint

        artifacts = ArchitectureArtifacts()
        artifacts.api_specs = {
            "/api/todos-get": APIEndpoint(
                path="/api/todos",
                method="GET",
                description="Return all todos",
                response_schema={"todos": ["object"]},
                authentication_required=True,
            ),
            "/api/todos-post": APIEndpoint(
                path="/api/todos",
                method="POST",
                description="Create a new todo",
                request_schema={"title": "string"},
                response_schema={"id": "string"},
                authentication_required=True,
            ),
        }

        assert "/api/todos-post" in artifacts.api_specs
        assert artifacts.api_specs["/api/todos-post"].method == "POST"

    def test_critical_sections_tracking(self):
        """Test critical sections tracking for context compaction."""
        artifacts = ArchitectureArtifacts()
        artifacts.critical_sections = {
            "UserAuthentication": "full",
            "PaymentProcessing": "full",
            "NotificationSystem": "summary"
        }

        assert artifacts.critical_sections["UserAuthentication"] == "full"
        assert artifacts.critical_sections["NotificationSystem"] == "summary"


@pytest.mark.unit
class TestDevelopmentArtifacts:
    """Test Development Agent artifacts."""

    def test_frontend_development_artifacts(self):
        """Test frontend development artifacts."""
        frontend = DevelopmentArtifacts()
        frontend.code_files = {
            "src/components/TodoList.tsx": "// React component code",
            "src/hooks/useTodos.ts": "// Custom hook code"
        }
        frontend.tests = {
            "src/components/__tests__/TodoList.test.tsx": "// Test code"
        }

        assert len(frontend.code_files) == 2
        assert len(frontend.tests) == 1

    def test_backend_development_artifacts(self):
        """Test backend development artifacts."""
        backend = DevelopmentArtifacts()
        backend.code_files = {
            "main.py": "# FastAPI app",
            "models/todo.py": "# SQLAlchemy models",
            "api/endpoints.py": "# API endpoints"
        }
        backend.status = TaskStatus.IN_PROGRESS

        assert len(backend.code_files) == 3
        assert backend.status == TaskStatus.IN_PROGRESS

    def test_development_section_isolation(self):
        """Test frontend and backend are isolated in development section."""
        dev_section = DevelopmentSection()

        dev_section.frontend.code_files["App.tsx"] = "// Frontend"
        dev_section.backend.code_files["main.py"] = "# Backend"

        assert "App.tsx" in dev_section.frontend.code_files
        assert "main.py" in dev_section.backend.code_files
        assert "App.tsx" not in dev_section.backend.code_files

    def test_development_dependencies(self):
        """Test dependency tracking in development artifacts."""
        artifacts = DevelopmentArtifacts()
        artifacts.depends_on = {
            "architecture_agent": 1,
            "planning_agent": 2
        }

        assert artifacts.depends_on["architecture_agent"] == 1
        assert len(artifacts.depends_on) == 2


@pytest.mark.unit
class TestTestingArtifacts:
    """Test QA Agent artifacts."""

    def test_testing_artifacts_initialization(self):
        """Test TestingArtifacts initialization."""
        artifacts = TestingArtifacts()

        assert artifacts.test_results is None
        assert artifacts.coverage_report is None
        assert artifacts.bug_reports == []
        assert artifacts.affected_agents == []

    def test_test_results_tracking(self):
        """Test test results tracking."""
        artifacts = TestingArtifacts()
        artifacts.test_results = {
            "total": 45,
            "passed": 42,
            "failed": 3,
            "skipped": 0,
            "coverage": 78.5
        }

        assert artifacts.test_results["passed"] == 42
        assert artifacts.test_results["coverage"] == 78.5

    def test_bug_reports(self):
        """Test bug report tracking."""
        artifacts = TestingArtifacts()
        artifacts.bug_reports = [
            {
                "bug_id": "BUG001",
                "title": "Auth token expiration not handled",
                "severity": "high",
                "affected_component": "AuthService"
            },
            {
                "bug_id": "BUG002",
                "title": "Form validation missing",
                "severity": "medium",
                "affected_component": "UserForm"
            }
        ]

        assert len(artifacts.bug_reports) == 2
        assert artifacts.bug_reports[0]["severity"] == "high"

    def test_error_analysis(self):
        """Test error analysis and root causes."""
        artifacts = TestingArtifacts()
        artifacts.error_analysis = {
            "root_causes": [
                "Missing error handling in API calls",
                "Unvalidated user input"
            ],
            "patterns": ["API timeout", "Null reference"],
            "affected_modules": ["AuthService", "UserForm"]
        }

        assert len(artifacts.error_analysis["root_causes"]) == 2
        assert "AuthService" in artifacts.error_analysis["affected_modules"]

    def test_restart_plan(self):
        """Test intelligent restart planning."""
        artifacts = TestingArtifacts()
        artifacts.restart_plan = {
            "restart_from_phase": "backend",
            "affected_agents": ["backend_dev"],
            "tasks_to_redo": ["BT001", "BT002"],
            "estimated_time_minutes": 30,
            "rationale": "Backend API implementation has contract issues"
        }

        assert artifacts.restart_plan["restart_from_phase"] == "backend"
        assert len(artifacts.restart_plan["tasks_to_redo"]) == 2


@pytest.mark.unit
class TestDocumentationArtifacts:
    """Test Documentation Agent artifacts."""

    def test_documentation_artifacts_initialization(self):
        """Test DocumentationArtifacts initialization."""
        artifacts = DocumentationArtifacts()

        assert artifacts.readme is None
        assert artifacts.api_docs is None
        assert artifacts.architecture_docs is None
        assert artifacts.deployment_guide is None
        assert artifacts.user_guide is None

    def test_documentation_content(self):
        """Test populated documentation artifacts."""
        artifacts = DocumentationArtifacts(
            readme="# Todo App\n\nA simple todo application",
            api_docs="## API Reference\n\n### GET /api/todos",
            deployment_guide="## Deployment\n\n1. Install dependencies"
        )

        assert "Todo App" in artifacts.readme
        assert "API Reference" in artifacts.api_docs
        assert "Install dependencies" in artifacts.deployment_guide


@pytest.mark.unit
class TestExecutionStatusTracking:
    """Test execution status tracking."""

    def test_agent_execution_status(self):
        """Test individual agent execution status."""
        status = AgentExecutionStatus(
            agent_id="planning_001",
            status=ExecutionStatus.IN_PROGRESS,
            version=1
        )

        assert status.agent_id == "planning_001"
        assert status.status == ExecutionStatus.IN_PROGRESS
        assert status.version == 1

    def test_execution_status_tracker(self):
        """Test execution status tracker."""
        tracker = ExecutionStatusTracker()

        tracker.update_agent_status("planning_001", ExecutionStatus.IN_PROGRESS)
        tracker.update_agent_status("architecture_001", ExecutionStatus.PENDING)

        assert tracker.get_agent_status("planning_001").status == ExecutionStatus.IN_PROGRESS
        assert len(tracker.agents) == 2

    def test_version_tracking(self):
        """Test version tracking for agent outputs."""
        tracker = ExecutionStatusTracker()

        tracker.update_agent_status("planning_001", ExecutionStatus.COMPLETED, version=1)
        tracker.update_agent_status("planning_001", ExecutionStatus.IN_PROGRESS, version=2)

        status = tracker.get_agent_status("planning_001")
        assert status.version == 2
        assert status.status == ExecutionStatus.IN_PROGRESS

    def test_dependency_tracking(self):
        """Test version dependencies between agents."""
        status = AgentExecutionStatus(
            agent_id="frontend_001",
            status=ExecutionStatus.PENDING,
            depends_on={"architecture_001": 1, "planning_001": 1}
        )

        assert status.depends_on["architecture_001"] == 1
        assert len(status.depends_on) == 2


@pytest.mark.unit
class TestTaskManagement:
    """Test task management in state."""

    def test_create_task_record(self):
        """Test creating a task record."""
        state = create_initial_state("test_001", "Test request")
        task = state.create_task_record(
            task_id="T001",
            agent_id="planning_001",
            phase=AgentPhase.PLANNING
        )

        assert task.task_id == "T001"
        assert task.agent_id == "planning_001"
        assert task.phase == AgentPhase.PLANNING
        assert task.status == TaskStatus.PENDING

    def test_get_task(self):
        """Test retrieving a task from state."""
        state = create_initial_state("test_001", "Test request")
        task1 = state.create_task_record("T001", "planning_001", AgentPhase.PLANNING)
        task2 = state.create_task_record("T002", "arch_001", AgentPhase.ARCHITECTURE)

        retrieved = state.get_task("T001")
        assert retrieved.task_id == "T001"
        assert retrieved.agent_id == "planning_001"

        assert state.get_task("T999") is None

    def test_task_dependencies(self):
        """Test task dependency tracking."""
        task = TaskRecord(
            task_id="T002",
            agent_id="frontend_001",
            phase=AgentPhase.FRONTEND,
            status=TaskStatus.PENDING,
            depends_on=["T001"]
        )

        assert "T001" in task.depends_on
        assert task.blocks == []

    def test_task_blocking(self):
        """Test task blocking relationships."""
        task = TaskRecord(
            task_id="T001",
            agent_id="arch_001",
            phase=AgentPhase.ARCHITECTURE,
            status=TaskStatus.PENDING,
            blocks=["T002", "T003"]
        )

        assert len(task.blocks) == 2
        assert "T002" in task.blocks


@pytest.mark.unit
class TestMessageManagement:
    """Test message and communication tracking."""

    def test_add_message(self):
        """Test adding messages to state."""
        state = create_initial_state("test_001", "Test request")

        message = AgentMessage(
            agent_id="planning_001",
            role="Planning Agent",
            content="Planning phase complete"
        )

        state.add_message(message)

        assert len(state.messages) == 1
        assert state.messages[0].agent_id == "planning_001"

    def test_message_timestamp(self):
        """Test message timestamp tracking."""
        message = AgentMessage(
            agent_id="planning_001",
            role="Planning Agent",
            content="Complete"
        )

        assert isinstance(message.timestamp, datetime)
        assert message.timestamp is not None

    def test_message_artifacts(self):
        """Test message artifact attachments."""
        message = AgentMessage(
            agent_id="arch_001",
            role="Architecture Agent",
            content="Architecture designed",
            artifacts={
                "component_specs": {"TodoList": {"type": "React.FC"}},
                "api_endpoints": {"/api/todos": {"method": "GET"}}
            }
        )

        assert "component_specs" in message.artifacts
        assert message.artifacts["component_specs"]["TodoList"]["type"] == "React.FC"


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in state."""

    def test_add_error(self):
        """Test adding errors to state (errors are now structured AgentError objects)."""
        state = create_initial_state("test_001", "Test request")

        state.add_error("Connection timeout")
        state.add_error("Database unavailable")

        assert len(state.errors) == 2
        # errors are AgentError objects; check the message field
        assert state.errors[0].message == "Connection timeout"
        assert state.errors[1].message == "Database unavailable"

    def test_error_tracking_updates_timestamp(self):
        """Test that adding errors updates last_modified_at."""
        state = create_initial_state("test_001", "Test request")
        original_time = state.metadata.last_modified_at

        import time
        time.sleep(0.01)

        state.add_error("Test error")

        assert state.metadata.last_modified_at > original_time

    def test_retry_count_tracking(self):
        """Test retry count for error recovery."""
        state = create_initial_state("test_001", "Test request")

        assert state.retry_count == 0

        state.retry_count = 1
        assert state.retry_count == 1

        state.retry_count += 1
        assert state.retry_count == 2


@pytest.mark.unit
class TestPhaseTransitions:
    """Test state phase transitions."""

    def test_mark_phase_complete(self):
        """Test marking a phase as complete."""
        state = create_initial_state("test_001", "Test request")
        assert state.metadata.current_phase == AgentPhase.PLANNING

        state.mark_phase_complete(AgentPhase.PLANNING, AgentPhase.ARCHITECTURE)

        assert state.metadata.current_phase == AgentPhase.ARCHITECTURE

    def test_phase_progression(self):
        """Test typical phase progression."""
        state = create_initial_state("test_001", "Test request")

        assert state.metadata.current_phase == AgentPhase.PLANNING

        state.mark_phase_complete(AgentPhase.PLANNING, AgentPhase.ARCHITECTURE)
        assert state.metadata.current_phase == AgentPhase.ARCHITECTURE

        state.mark_phase_complete(AgentPhase.ARCHITECTURE, AgentPhase.FRONTEND)
        assert state.metadata.current_phase == AgentPhase.FRONTEND

        state.mark_phase_complete(AgentPhase.FRONTEND, AgentPhase.QA)
        assert state.metadata.current_phase == AgentPhase.QA

    def test_completion_flag(self):
        """Test workflow completion flag."""
        state = create_initial_state("test_001", "Test request")
        assert state.is_complete is False

        state.is_complete = True
        assert state.is_complete is True


@pytest.mark.unit
class TestArtifactMetadata:
    """Test artifact metadata tracking."""

    def test_artifact_metadata_creation(self):
        """Test creating artifact metadata."""
        metadata = ArtifactMetadata(
            artifact_name="requirements.md",
            artifact_type="requirements",
            size_bytes=2048,
            version=1
        )

        assert metadata.artifact_name == "requirements.md"
        assert metadata.artifact_type == "requirements"
        assert metadata.size_bytes == 2048
        assert metadata.in_state is True

    def test_artifact_manifest(self):
        """Test artifact manifest management."""
        manifest = ArtifactManifest()

        meta1 = ArtifactMetadata(
            artifact_name="requirements.md",
            artifact_type="requirements",
            size_bytes=2048
        )
        meta2 = ArtifactMetadata(
            artifact_name="api_specs.json",
            artifact_type="api_specs",
            size_bytes=4096
        )

        manifest.register_artifact("requirements", meta1)
        manifest.register_artifact("api_specs", meta2)

        assert len(manifest.artifacts) == 2
        assert manifest.get_artifact_info("requirements") == meta1

    def test_compression_tracking(self):
        """Test compression statistics tracking."""
        stats = CompressionStats(
            total_artifact_size=1000000,
            compressed_size=150000,
            compression_ratio=0.15,
            tokens_saved=5000
        )

        assert stats.compression_ratio == 0.15
        assert stats.tokens_saved == 5000


@pytest.mark.unit
class TestStateUpdates:
    """Test state update application."""

    def test_apply_state_update(self):
        """Test applying state updates."""
        state = create_initial_state("test_001", "Test request")

        update = StateUpdate(
            planning_artifacts=PlanningArtifacts(
                requirements="Updated requirements"
            ),
            current_phase=AgentPhase.ARCHITECTURE,
            current_agent="arch_001"
        )

        updated_state = apply_state_update(state, update)

        assert updated_state.planning_artifacts.requirements == "Updated requirements"
        assert updated_state.metadata.current_phase == AgentPhase.ARCHITECTURE
        assert updated_state.metadata.current_agent == "arch_001"

    def test_apply_message_update(self):
        """Test applying message updates."""
        state = create_initial_state("test_001", "Test request")

        message = AgentMessage(
            agent_id="planning_001",
            role="Planning Agent",
            content="Planning complete"
        )

        update = StateUpdate(message=message)
        updated_state = apply_state_update(state, update)

        assert len(updated_state.messages) == 1
        assert updated_state.messages[0].content == "Planning complete"

    def test_apply_error_update(self):
        """Test applying error updates (strings are auto-converted to AgentError)."""
        state = create_initial_state("test_001", "Test request")

        update = StateUpdate(
            errors=["Error 1", "Error 2"]
        )

        updated_state = apply_state_update(state, update)

        assert len(updated_state.errors) == 2
        # errors are AgentError objects; plain strings are auto-converted
        messages = [e.message for e in updated_state.errors]
        assert "Error 1" in messages
        assert "Error 2" in messages


@pytest.mark.unit
class TestGetArtifactsBySection:
    """Test getting artifacts by section."""

    def test_get_planning_section(self):
        """Test retrieving planning artifacts."""
        state = create_initial_state("test_001", "Test request")
        state.planning_artifacts.requirements = "Test requirements"

        section = state.get_artifacts_by_section("planning")

        assert section["requirements"] == "Test requirements"

    def test_get_all_sections(self):
        """Test retrieving all artifact sections."""
        state = create_initial_state("test_001", "Test request")

        sections = [
            "planning",
            "architecture",
            "development_frontend",
            "development_backend",
            "testing",
            "documentation"
        ]

        for section in sections:
            artifacts = state.get_artifacts_by_section(section)
            assert isinstance(artifacts, dict)

    def test_invalid_section_returns_empty(self):
        """Test that invalid section returns empty dict."""
        state = create_initial_state("test_001", "Test request")

        section = state.get_artifacts_by_section("invalid_section")

        assert section == {}
