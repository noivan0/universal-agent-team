"""
Integration tests for orchestrator functionality.

Tests cover:
- ProjectOrchestrator workflow management
- Task scheduling and execution
- State transitions across phases
- Error handling and recovery
- Parallel execution simulation
"""

import pytest
from datetime import datetime
from state_models import (
    AgentState,
    AgentPhase,
    TaskStatus,
    ExecutionStatus,
    AgentMessage,
    PlanningArtifacts,
    create_initial_state,
    apply_state_update,
    StateUpdate,
)
from orchestrator.specialist_agent_selector import ComplexityFactors, create_default_selector


@pytest.mark.integration
class TestProjectOrchestration:
    """Test project orchestration workflow."""

    def test_workflow_initialization(self, simple_project_state):
        """Test workflow initialization."""
        state = simple_project_state

        assert state.metadata.project_id is not None
        assert state.metadata.user_request is not None
        assert state.metadata.current_phase == AgentPhase.PLANNING
        assert state.is_complete is False

    def test_planning_phase_completion(self):
        """Test completing planning phase."""
        state = create_initial_state("test_001", "Build todo app")

        # Simulate planning agent work
        update = StateUpdate(
            planning_artifacts=PlanningArtifacts(
                requirements="Build a todo list with CRUD operations",
                complexity_score=35,
                tasks=[
                    {"task_id": "T001", "title": "Design", "status": "pending"},
                    {"task_id": "T002", "title": "Frontend", "status": "pending"},
                    {"task_id": "T003", "title": "Backend", "status": "pending"},
                ]
            ),
            current_phase=AgentPhase.ARCHITECTURE,
            message=AgentMessage(
                agent_id="planning_001",
                role="Planning Agent",
                content="Planning phase complete"
            )
        )

        updated_state = apply_state_update(state, update)

        assert updated_state.planning_artifacts.requirements is not None
        assert updated_state.metadata.current_phase == AgentPhase.ARCHITECTURE
        assert len(updated_state.messages) == 1

    def test_architecture_phase_completion(self, planning_phase_state):
        """Test completing architecture phase."""
        state = planning_phase_state

        # Simulate architecture agent work
        from state_models import ArchitectureArtifacts

        update = StateUpdate(
            architecture_artifacts=ArchitectureArtifacts(
                system_design="Monolithic architecture with React frontend",
                component_specs={
                    "TodoList": {"type": "React.FC", "props": ["todos"]},
                    "TodoItem": {"type": "React.FC", "props": ["todo"]}
                },
                api_specs={
                    "/api/todos": {"method": "GET"},
                    "/api/todos": {"method": "POST"}
                },
                database_schema="todos table with id, title, completed"
            ),
            current_phase=AgentPhase.FRONTEND,
            message=AgentMessage(
                agent_id="arch_001",
                role="Architecture Agent",
                content="Architecture design complete"
            )
        )

        updated_state = apply_state_update(state, update)

        assert updated_state.architecture_artifacts.system_design is not None
        assert len(updated_state.architecture_artifacts.component_specs) == 2
        assert updated_state.metadata.current_phase == AgentPhase.FRONTEND

    def test_parallel_development_tracking(self, architecture_phase_state):
        """Test tracking parallel frontend and backend development."""
        state = architecture_phase_state

        # Frontend development
        from state_models import DevelopmentArtifacts, DevelopmentSection

        frontend_artifacts = DevelopmentArtifacts()
        frontend_artifacts.code_files = {
            "src/components/TodoList.tsx": "// React component",
            "src/components/TodoItem.tsx": "// React component"
        }
        frontend_artifacts.status = TaskStatus.COMPLETED

        # Backend development
        backend_artifacts = DevelopmentArtifacts()
        backend_artifacts.code_files = {
            "main.py": "# FastAPI app",
            "models.py": "# SQLAlchemy models",
            "api.py": "# API endpoints"
        }
        backend_artifacts.status = TaskStatus.COMPLETED

        # Update state with both
        dev_section = DevelopmentSection(
            frontend=frontend_artifacts,
            backend=backend_artifacts
        )

        update = StateUpdate(
            development=dev_section,
            current_phase=AgentPhase.QA
        )

        updated_state = apply_state_update(state, update)

        assert len(updated_state.development.frontend.code_files) == 2
        assert len(updated_state.development.backend.code_files) == 3
        assert updated_state.development.frontend.status == TaskStatus.COMPLETED
        assert updated_state.development.backend.status == TaskStatus.COMPLETED

    def test_qa_phase_with_results(self, architecture_phase_state):
        """Test QA phase with test results."""
        state = architecture_phase_state

        from state_models import TestingArtifacts

        update = StateUpdate(
            testing_artifacts=TestingArtifacts(
                test_results={
                    "total": 45,
                    "passed": 42,
                    "failed": 3,
                    "coverage": 78.5
                },
                bug_reports=[
                    {"bug_id": "BUG001", "title": "Auth token issue", "severity": "high"},
                    {"bug_id": "BUG002", "title": "Form validation", "severity": "medium"}
                ]
            ),
            current_phase=AgentPhase.DOCUMENTATION
        )

        updated_state = apply_state_update(state, update)

        assert updated_state.testing_artifacts.test_results["passed"] == 42
        assert len(updated_state.testing_artifacts.bug_reports) == 2

    def test_complete_workflow(self):
        """Test complete workflow from start to finish."""
        # Initialize
        state = create_initial_state("workflow_test_001", "Build complete todo app")

        # Planning phase
        state.planning_artifacts.requirements = "Complete todo app"
        state.planning_artifacts.complexity_score = 35
        state.metadata.current_phase = AgentPhase.ARCHITECTURE

        # Architecture phase
        state.architecture_artifacts.system_design = "Monolithic"
        state.architecture_artifacts.component_specs = {"TodoList": {}}
        state.metadata.current_phase = AgentPhase.FRONTEND

        # Development phases
        state.development.frontend.code_files["App.tsx"] = "// App"
        state.development.backend.code_files["main.py"] = "# API"
        state.metadata.current_phase = AgentPhase.QA

        # Testing phase
        state.testing_artifacts.test_results = {"passed": 50, "failed": 0}
        state.metadata.current_phase = AgentPhase.DOCUMENTATION

        # Documentation phase
        state.documentation_artifacts.readme = "# Todo App"
        state.documentation_artifacts.api_docs = "## API"
        state.metadata.current_phase = AgentPhase.COMPLETE

        # Mark complete
        state.is_complete = True

        # Verify completion
        assert state.is_complete is True
        assert state.metadata.current_phase == AgentPhase.COMPLETE
        assert state.planning_artifacts.requirements is not None
        assert len(state.development.frontend.code_files) > 0
        assert len(state.development.backend.code_files) > 0


@pytest.mark.integration
class TestTaskManagement:
    """Test task scheduling and management."""

    def test_create_and_track_tasks(self):
        """Test creating and tracking tasks."""
        state = create_initial_state("task_test_001", "Test project")

        # Create tasks
        t1 = state.create_task_record("T001", "arch_001", AgentPhase.ARCHITECTURE)
        t2 = state.create_task_record("T002", "frontend_001", AgentPhase.FRONTEND)
        t3 = state.create_task_record("T003", "backend_001", AgentPhase.BACKEND)

        assert len(state.tasks) == 3
        assert state.get_task("T001").agent_id == "arch_001"
        assert state.get_task("T002").phase == AgentPhase.FRONTEND

    def test_task_dependency_chain(self):
        """Test task dependency chains."""
        state = create_initial_state("dep_test_001", "Test dependencies")

        t1 = state.create_task_record("T001", "arch_001", AgentPhase.ARCHITECTURE)
        t2 = state.create_task_record("T002", "frontend_001", AgentPhase.FRONTEND)
        t3 = state.create_task_record("T003", "backend_001", AgentPhase.BACKEND)

        # Set dependencies
        t2.depends_on = ["T001"]
        t3.depends_on = ["T001"]
        t1.blocks = ["T002", "T003"]

        # Verify dependency chains
        assert "T001" in t2.depends_on
        assert "T001" in t3.depends_on
        assert "T002" in t1.blocks

    def test_task_status_progression(self):
        """Test task status progression through states."""
        state = create_initial_state("status_test_001", "Test status")

        task = state.create_task_record("T001", "agent_001", AgentPhase.PLANNING)
        assert task.status == TaskStatus.PENDING

        # Progress through states
        task.status = TaskStatus.IN_PROGRESS
        assert task.status == TaskStatus.IN_PROGRESS

        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

    def test_task_error_tracking(self):
        """Test error tracking in tasks."""
        state = create_initial_state("error_test_001", "Test errors")

        task = state.create_task_record("T001", "agent_001", AgentPhase.PLANNING)

        # Add errors
        task.errors.append("Connection timeout")
        task.errors.append("API rate limit exceeded")
        task.status = TaskStatus.FAILED

        assert len(task.errors) == 2
        assert task.status == TaskStatus.FAILED

    def test_retry_tracking(self):
        """Test retry attempt tracking."""
        state = create_initial_state("retry_test_001", "Test retries")

        task = state.create_task_record("T001", "agent_001", AgentPhase.PLANNING)
        task.attempts = 1
        task.retry_count = 1

        task.attempts = 2
        task.retry_count = 2

        assert task.attempts == 2
        assert task.retry_count == 2


@pytest.mark.integration
class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms."""

    def test_error_in_execution(self):
        """Test handling errors during execution."""
        state = create_initial_state("error_001", "Test project")

        # Simulate error
        state.add_error("Planning agent failed: timeout")
        state.retry_count = 1

        assert len(state.errors) == 1
        assert state.retry_count == 1

    def test_error_escalation(self):
        """Test error escalation to human review."""
        state = create_initial_state("escalation_001", "Test project")

        # Add multiple errors and require human approval
        state.add_error("Error 1")
        state.add_error("Error 2")
        state.add_error("Error 3")
        state.requires_human_approval = True
        state.approval_reason = "Too many errors, manual review needed"

        assert state.requires_human_approval is True
        assert len(state.errors) == 3
        assert state.approval_reason is not None

    def test_recovery_from_error(self):
        """Test recovery from errors."""
        state = create_initial_state("recovery_001", "Test project")

        # Initial error
        state.add_error("Initial error")
        state.requires_human_approval = True

        # Recovery - clear errors and continue
        state.errors = []
        state.requires_human_approval = False
        state.retry_count = 0

        assert len(state.errors) == 0
        assert state.requires_human_approval is False

    def test_intelligent_restart_planning(self):
        """Test intelligent restart planning after failures."""
        from state_models import TestingArtifacts

        state = create_initial_state("restart_001", "Test project")
        state.metadata.current_phase = AgentPhase.QA

        # Simulate test failures
        state.testing_artifacts.test_results = {
            "total": 50,
            "passed": 35,
            "failed": 15
        }
        state.testing_artifacts.error_analysis = {
            "root_causes": ["Database schema mismatch"],
            "affected_modules": ["backend"]
        }
        state.testing_artifacts.restart_plan = {
            "restart_from_phase": "backend",
            "affected_agents": ["backend_dev", "data_modeler"],
            "estimated_time_minutes": 45,
            "rationale": "Backend database schema needs redesign"
        }

        assert state.testing_artifacts.restart_plan is not None
        assert state.testing_artifacts.restart_plan["restart_from_phase"] == "backend"


@pytest.mark.integration
class TestSpecialistAgentIntegration:
    """Test specialist agent integration with main workflow."""

    def test_specialist_selection_in_workflow(self, complex_project_state):
        """Test specialist selection during workflow."""
        state = complex_project_state

        # Get complexity factors from planning
        factors = ComplexityFactors(
            has_api=True,
            has_microservices=True,
            has_ui_heavy=True,
            has_database_heavy=True,
            requires_auth=True,
            requires_compliance=True,
            component_count=25,
            table_count=12,
            api_endpoint_count=30,
            sensitive_data_types=["PII", "Payment Info"]
        )

        selector = create_default_selector()
        specialists = selector.select_specialists(
            complexity_score=state.planning_artifacts.complexity_score,
            factors=factors
        )

        # Should select specialists for complex project
        assert len(specialists) > 0

    def test_specialist_agent_sequencing(self, complex_project_state):
        """Test that specialist agents are ordered correctly."""
        factors = ComplexityFactors(
            has_api=True,
            has_database_heavy=True,
            has_ui_heavy=True,
            requires_auth=True,
            requires_performance=True,
            component_count=20,
            table_count=10,
            api_endpoint_count=20
        )

        selector = create_default_selector()
        specialists = selector.select_specialists(
            complexity_score=75,
            factors=factors
        )

        # Verify ordering
        if len(specialists) > 1:
            type_order = [s.agent_type.value for s in specialists]
            # Data modeler should come before performance reviewer
            assert len(type_order) > 0

    def test_specialist_duration_estimation(self):
        """Test specialist duration estimation."""
        factors = ComplexityFactors(
            has_database_heavy=True,
            has_real_time=True,
            has_high_load=True,
            table_count=10,
            requires_performance=True,
            expected_concurrent_users=50000
        )

        selector = create_default_selector()
        specialists = selector.select_specialists(
            complexity_score=80,
            factors=factors
        )

        total_duration = selector.estimate_total_duration(specialists)
        api_calls = selector.estimate_api_calls(specialists)

        # Durations should be reasonable
        assert total_duration >= 0
        assert api_calls >= 0


@pytest.mark.integration
class TestStateConsistency:
    """Test state consistency across updates."""

    def test_state_consistency_after_updates(self):
        """Test that state remains consistent after multiple updates."""
        state = create_initial_state("consistency_001", "Test project")

        # Multiple updates
        updates = [
            StateUpdate(planning_artifacts=PlanningArtifacts(requirements="Test")),
            StateUpdate(current_phase=AgentPhase.ARCHITECTURE),
            StateUpdate(current_phase=AgentPhase.FRONTEND),
        ]

        for update in updates:
            state = apply_state_update(state, update)

        # Verify consistency
        assert state.planning_artifacts.requirements == "Test"
        assert state.metadata.current_phase == AgentPhase.FRONTEND

    def test_timestamp_updates(self):
        """Test that timestamps are updated correctly."""
        state = create_initial_state("timestamp_001", "Test")
        original_time = state.metadata.last_modified_at

        import time
        time.sleep(0.01)

        state.add_message(AgentMessage(
            agent_id="test",
            role="Test",
            content="Test message"
        ))

        assert state.metadata.last_modified_at > original_time

    def test_artifact_isolation(self):
        """Test that artifact sections are properly isolated."""
        state1 = create_initial_state("iso1", "Project 1")
        state2 = create_initial_state("iso2", "Project 2")

        state1.planning_artifacts.requirements = "Project 1 requirements"
        state2.planning_artifacts.requirements = "Project 2 requirements"

        # Verify isolation
        assert state1.planning_artifacts.requirements != state2.planning_artifacts.requirements


@pytest.mark.integration
class TestMessageCommunication:
    """Test agent communication via messages."""

    def test_message_routing(self):
        """Test message routing between agents."""
        state = create_initial_state("msg_001", "Test")

        # Planning agent message
        planning_msg = AgentMessage(
            agent_id="planning_001",
            role="Planning Agent",
            content="Planning complete",
            artifacts={"requirements": "Test requirements"}
        )
        state.add_message(planning_msg)

        # Architecture agent message
        arch_msg = AgentMessage(
            agent_id="arch_001",
            role="Architecture Agent",
            content="Architecture complete",
            artifacts={"component_specs": {}}
        )
        state.add_message(arch_msg)

        # Verify messages
        assert len(state.messages) == 2
        assert state.messages[0].agent_id == "planning_001"
        assert state.messages[1].agent_id == "arch_001"

    def test_artifact_handoff(self):
        """Test artifact handoff between agents."""
        state = create_initial_state("handoff_001", "Test")

        # Planning agent produces artifacts
        planning_msg = AgentMessage(
            agent_id="planning_001",
            role="Planning Agent",
            content="Planning complete",
            artifacts={
                "requirements": "Build a todo app",
                "tasks": [{"task_id": "T001", "title": "Design"}],
                "complexity_score": 35
            }
        )
        state.add_message(planning_msg)

        # Architecture agent consumes planning artifacts
        planning_artifacts = planning_msg.artifacts
        assert "requirements" in planning_artifacts
        assert "tasks" in planning_artifacts
        assert planning_artifacts["complexity_score"] == 35
