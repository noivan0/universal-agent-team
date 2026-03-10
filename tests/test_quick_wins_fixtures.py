"""
Unit tests for Quick Wins fixture factories (Quick Win 5).

Tests cover:
- ProjectConfigFactory
- AgentStateFactory
- Fixture usage patterns
"""

import pytest
from state_models import AgentPhase, AgentState
from orchestrator.project_registry import ProjectConfig, ProjectStatus, ProjectPhase


@pytest.mark.unit
class TestProjectConfigFactory:
    """Test ProjectConfigFactory for creating test configs (Quick Win 5)."""

    def test_factory_create_default(self, project_config_factory):
        """Test creating config with default values."""
        config = project_config_factory.create()

        assert config is not None
        assert config.project_id is not None
        assert config.user_request is not None
        assert config.team_id == "universal-agents-v1"
        assert config.status == ProjectStatus.PENDING
        assert config.complexity_score == 50

    def test_factory_create_custom(self, project_config_factory):
        """Test creating config with custom values."""
        config = project_config_factory.create(
            project_id="custom_proj",
            user_request="Custom request",
            complexity_score=75,
            status=ProjectStatus.IN_PROGRESS
        )

        assert config.project_id == "custom_proj"
        assert config.user_request == "Custom request"
        assert config.complexity_score == 75
        assert config.status == ProjectStatus.IN_PROGRESS

    def test_factory_auto_increment_ids(self, project_config_factory):
        """Test factory auto-increments project IDs."""
        config1 = project_config_factory.create()
        config2 = project_config_factory.create()
        config3 = project_config_factory.create()

        # IDs should be unique
        ids = {config1.project_id, config2.project_id, config3.project_id}
        assert len(ids) == 3

    def test_factory_reset(self, project_config_factory):
        """Test factory reset functionality."""
        config1 = project_config_factory.create()
        project_config_factory.reset()
        config2 = project_config_factory.create()

        # After reset, counter should restart
        assert config1.project_id != config2.project_id

    def test_factory_multiple_instances_independent(self):
        """Test that multiple factory calls are independent."""
        from conftest import ProjectConfigFactory

        config1 = ProjectConfigFactory.create(project_id="proj1")
        config2 = ProjectConfigFactory.create(project_id="proj2")

        assert config1.project_id == "proj1"
        assert config2.project_id == "proj2"


@pytest.mark.unit
class TestAgentStateFactory:
    """Test AgentStateFactory for creating test states (Quick Win 5)."""

    def test_factory_create_simple(self, agent_state_factory):
        """Test creating simple state."""
        state = agent_state_factory.create_simple()

        assert isinstance(state, AgentState)
        assert state.metadata.project_id == "test_simple_001"
        assert state.metadata.user_request == "Simple test project"

    def test_factory_create_with_planning(self, agent_state_factory):
        """Test creating state after planning."""
        state = agent_state_factory.create_with_planning()

        assert state.planning_artifacts.requirements is not None
        assert len(state.planning_artifacts.tasks) > 0
        assert state.metadata.current_phase == AgentPhase.PLANNING

    def test_factory_create_with_architecture(self, agent_state_factory):
        """Test creating state after architecture."""
        state = agent_state_factory.create_with_architecture()

        assert state.architecture_artifacts.system_design is not None
        assert len(state.architecture_artifacts.component_specs) > 0
        assert len(state.architecture_artifacts.api_specs) > 0
        assert state.metadata.current_phase == AgentPhase.ARCHITECTURE

    def test_factory_create_full(self, agent_state_factory):
        """Test creating state with all phases."""
        state = agent_state_factory.create_full()

        # Should have code files
        assert len(state.development.frontend.code_files) > 0
        assert len(state.development.backend.code_files) > 0

        # Should have test results
        assert state.testing_artifacts.test_results["total"] > 0
        assert state.testing_artifacts.test_results["passed"] > 0

        # Should have documentation
        assert state.documentation_artifacts.readme is not None

        # Should be complete
        assert state.metadata.current_phase == AgentPhase.COMPLETE

    def test_factory_create_complex(self, agent_state_factory):
        """Test creating state for complex project."""
        state = agent_state_factory.create_complex()

        assert state.planning_artifacts.complexity_score > 50
        assert len(state.planning_artifacts.complexity_factors) > 0

    def test_state_from_factory_is_valid(self, agent_state_factory):
        """Test that states created by factory are valid."""
        state = agent_state_factory.create_with_architecture()

        # Should have valid metadata
        assert state.metadata.project_id is not None
        assert state.metadata.user_request is not None

        # Should be properly typed
        assert isinstance(state.planning_artifacts, PlanningArtifacts)
        assert isinstance(state.architecture_artifacts, ArchitectureArtifacts)


# Import needed classes for testing
from state_models import (
    PlanningArtifacts,
    ArchitectureArtifacts,
)


@pytest.mark.unit
class TestFactoryUsagePatterns:
    """Test common usage patterns for factories."""

    def test_factory_fixture_in_test(self, project_config_factory):
        """Test using factory fixture in test."""
        config = project_config_factory.create(
            user_request="Build a todo app"
        )

        assert config.user_request == "Build a todo app"
        assert config.project_id is not None

    def test_multiple_factory_calls_in_test(self, agent_state_factory):
        """Test creating multiple states in single test."""
        state1 = agent_state_factory.create_simple()
        state2 = agent_state_factory.create_with_planning()
        state3 = agent_state_factory.create_full()

        # All should be valid
        assert state1.metadata.project_id is not None
        assert state2.planning_artifacts.requirements is not None
        assert state3.metadata.current_phase == AgentPhase.COMPLETE

    def test_factory_for_parametrized_tests(self, project_config_factory):
        """Test using factory in parametrized test scenarios."""
        complexities = [30, 50, 75, 90]
        configs = [
            project_config_factory.create(complexity_score=c)
            for c in complexities
        ]

        for i, config in enumerate(configs):
            assert config.complexity_score == complexities[i]

    def test_factory_reduces_boilerplate(self, agent_state_factory):
        """Test that factory reduces test boilerplate."""
        # Without factory, would need to manually set all fields
        # With factory, just one call
        state = agent_state_factory.create_with_architecture()

        # Verify all needed fields are set
        assert state.planning_artifacts is not None
        assert state.architecture_artifacts is not None
        assert state.development is not None
