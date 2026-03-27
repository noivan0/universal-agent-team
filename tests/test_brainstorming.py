"""
Unit tests for the Collective Brainstorming Phase.

Tests cover:
- BrainstormingPerspective model serialization/deserialization
- BrainstormingArtifacts model (defaults, population, serialization)
- BrainstormingAgentOutput schema validation (blocking on missing fields)
- BrainstormingSynthesisOutput schema validation
- _apply_brainstorming_perspective() merge logic
- AgentPhase.BRAINSTORMING enum value
- AgentState.brainstorming_artifacts field
- StateUpdate.brainstorming_artifacts field
- _build_project_context() includes brainstorming insights when present
- BRAINSTORMING_ROLES constant exists in run_workflow
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

import pytest

# Ensure workspace is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from state_models import (
    AgentPhase,
    AgentState,
    BrainstormingArtifacts,
    BrainstormingPerspective,
    StateUpdate,
    create_initial_state,
    apply_state_update,
)
from artifact_schemas import (
    BrainstormingAgentOutput,
    BrainstormingSynthesisOutput,
    SchemaValidator,
)


# ============================================================================
# AgentPhase.BRAINSTORMING
# ============================================================================

class TestAgentPhaseBrainstorming:
    def test_brainstorming_enum_exists(self):
        assert AgentPhase.BRAINSTORMING == "brainstorming"

    def test_brainstorming_is_first_listed(self):
        phases = list(AgentPhase)
        assert phases[0] == AgentPhase.BRAINSTORMING


# ============================================================================
# BrainstormingPerspective model
# ============================================================================

class TestBrainstormingPerspective:
    def _make_perspective(self, role: str = "architecture") -> BrainstormingPerspective:
        return BrainstormingPerspective(
            agent_role=role,
            domain_concerns=["Concern A", "Concern B"],
            preliminary_design={"pattern": "monolith", "tech": "FastAPI"},
            recommended_approaches=["Approach X"],
            risks_and_challenges=["Risk 1"],
            dependencies_on_others=["Needs backend API spec"],
        )

    def test_create_valid_perspective(self):
        p = self._make_perspective()
        assert p.agent_role == "architecture"
        assert len(p.domain_concerns) == 2
        assert "pattern" in p.preliminary_design

    def test_defaults_are_empty_lists_and_dicts(self):
        p = BrainstormingPerspective(agent_role="qa")
        assert p.domain_concerns == []
        assert p.preliminary_design == {}
        assert p.recommended_approaches == []
        assert p.risks_and_challenges == []
        assert p.dependencies_on_others == []

    def test_serialization_round_trip(self):
        p = self._make_perspective("frontend")
        dumped = p.model_dump()
        restored = BrainstormingPerspective(**dumped)
        assert restored.agent_role == p.agent_role
        assert restored.domain_concerns == p.domain_concerns
        assert restored.preliminary_design == p.preliminary_design

    def test_json_serialization(self):
        p = self._make_perspective()
        json_str = p.model_dump_json()
        data = json.loads(json_str)
        assert data["agent_role"] == "architecture"
        assert isinstance(data["domain_concerns"], list)


# ============================================================================
# BrainstormingArtifacts model
# ============================================================================

class TestBrainstormingArtifacts:
    def _make_artifacts(self) -> BrainstormingArtifacts:
        return BrainstormingArtifacts(
            perspectives={
                "architecture": BrainstormingPerspective(
                    agent_role="architecture",
                    domain_concerns=["Scalability"],
                    preliminary_design={"pattern": "microservices"},
                    recommended_approaches=["REST API"],
                ),
            },
            collective_consensus="Agreed to use React + FastAPI stack.",
            agreed_tech_stack={"frontend": "React", "backend": "FastAPI"},
            critical_decisions=["Use JWT auth", "PostgreSQL as primary DB"],
            early_risks=["Third-party API instability"],
            completed_at=datetime.now(timezone.utc),
        )

    def test_default_factory_produces_empty(self):
        ba = BrainstormingArtifacts()
        assert ba.perspectives == {}
        assert ba.collective_consensus is None
        assert ba.agreed_tech_stack is None
        assert ba.critical_decisions == []
        assert ba.early_risks == []
        assert ba.completed_at is None

    def test_create_populated_artifacts(self):
        ba = self._make_artifacts()
        assert "architecture" in ba.perspectives
        assert ba.collective_consensus.startswith("Agreed")
        assert ba.agreed_tech_stack["frontend"] == "React"
        assert len(ba.critical_decisions) == 2

    def test_serialization_round_trip(self):
        ba = self._make_artifacts()
        dumped = ba.model_dump()
        restored = BrainstormingArtifacts(**dumped)
        assert restored.collective_consensus == ba.collective_consensus
        assert "architecture" in restored.perspectives
        assert restored.agreed_tech_stack == ba.agreed_tech_stack

    def test_perspectives_are_deserialized_correctly(self):
        ba = self._make_artifacts()
        dumped = ba.model_dump()
        restored = BrainstormingArtifacts(**dumped)
        arch = restored.perspectives["architecture"]
        assert isinstance(arch, BrainstormingPerspective)
        assert arch.agent_role == "architecture"


# ============================================================================
# AgentState.brainstorming_artifacts field
# ============================================================================

class TestAgentStateBrainstormingField:
    def test_agent_state_has_brainstorming_artifacts(self):
        state = create_initial_state("proj_001", "Build a todo app")
        assert hasattr(state, "brainstorming_artifacts")
        assert isinstance(state.brainstorming_artifacts, BrainstormingArtifacts)

    def test_brainstorming_artifacts_default_is_empty(self):
        state = create_initial_state("proj_002", "Build a todo app")
        assert state.brainstorming_artifacts.perspectives == {}
        assert state.brainstorming_artifacts.collective_consensus is None

    def test_state_serialization_includes_brainstorming(self):
        state = create_initial_state("proj_003", "Build a todo app")
        state.brainstorming_artifacts = BrainstormingArtifacts(
            collective_consensus="Test consensus",
            agreed_tech_stack={"frontend": "Vue"},
        )
        json_str = state.model_dump_json()
        data = json.loads(json_str)
        assert "brainstorming_artifacts" in data
        assert data["brainstorming_artifacts"]["collective_consensus"] == "Test consensus"


# ============================================================================
# StateUpdate.brainstorming_artifacts field
# ============================================================================

class TestStateUpdateBrainstormingField:
    def test_state_update_has_brainstorming_field(self):
        update = StateUpdate()
        assert hasattr(update, "brainstorming_artifacts")
        assert update.brainstorming_artifacts is None

    def test_state_update_apply_brainstorming_artifacts(self):
        state = create_initial_state("proj_004", "Build a todo app")
        new_ba = BrainstormingArtifacts(
            collective_consensus="Collective consensus text",
            agreed_tech_stack={"frontend": "React", "backend": "FastAPI"},
            critical_decisions=["Decision 1"],
            early_risks=["Risk 1"],
        )
        update = StateUpdate(brainstorming_artifacts=new_ba)
        updated_state = apply_state_update(state, update)
        assert updated_state.brainstorming_artifacts.collective_consensus == "Collective consensus text"
        assert updated_state.brainstorming_artifacts.agreed_tech_stack["backend"] == "FastAPI"


# ============================================================================
# BrainstormingAgentOutput schema validation
# ============================================================================

class TestBrainstormingAgentOutputSchema:
    def _valid_output(self) -> Dict[str, Any]:
        return {
            "agent_role": "architecture",
            "domain_concerns": ["Scalability", "Security"],
            "preliminary_design": {"pattern": "monolith"},
            "recommended_approaches": ["Use REST", "Stateless design"],
            "risks_and_challenges": ["Tight deadline"],
            "dependencies_on_others": ["Need frontend component list"],
        }

    def test_valid_output_passes(self):
        output = BrainstormingAgentOutput(**self._valid_output())
        assert output.agent_role == "architecture"
        assert len(output.domain_concerns) == 2

    def test_missing_agent_role_raises(self):
        data = self._valid_output()
        del data["agent_role"]
        with pytest.raises(Exception):
            BrainstormingAgentOutput(**data)

    def test_schema_validator_for_brainstorming_agents(self):
        """SchemaValidator.validate_for_agent should accept valid brainstorming output."""
        for role_suffix in ["planning", "architecture", "frontend", "backend", "qa", "documentation"]:
            agent_id = f"brainstorming_{role_suffix}"
            valid_data = {
                "agent_role": role_suffix,
                "domain_concerns": ["Concern A"],
                "preliminary_design": {"key": "value"},
                "recommended_approaches": ["Approach X"],
                "risks_and_challenges": [],
                "dependencies_on_others": [],
            }
            error = SchemaValidator.validate_for_agent(agent_id, valid_data)
            assert error is None, f"Unexpected error for {agent_id}: {error}"

    def test_schema_validator_rejects_missing_agent_role(self):
        data = {
            "domain_concerns": ["Concern A"],
            "preliminary_design": {"key": "value"},
            "recommended_approaches": ["Approach X"],
        }
        error = SchemaValidator.validate_for_agent("brainstorming_architecture", data)
        assert error is not None, "Should reject output missing agent_role"


# ============================================================================
# BrainstormingSynthesisOutput schema validation
# ============================================================================

class TestBrainstormingSynthesisOutputSchema:
    def _valid_synthesis(self) -> Dict[str, Any]:
        return {
            "collective_consensus": "Agreed to use React + FastAPI with PostgreSQL.",
            "agreed_tech_stack": {"frontend": "React", "backend": "FastAPI"},
            "critical_decisions": ["Use JWT for auth", "REST API style"],
            "early_risks": ["Third-party dependency risk"],
        }

    def test_valid_synthesis_passes(self):
        output = BrainstormingSynthesisOutput(**self._valid_synthesis())
        assert output.collective_consensus.startswith("Agreed")
        assert output.agreed_tech_stack["frontend"] == "React"
        assert len(output.critical_decisions) == 2

    def test_missing_collective_consensus_raises(self):
        data = self._valid_synthesis()
        del data["collective_consensus"]
        with pytest.raises(Exception):
            BrainstormingSynthesisOutput(**data)

    def test_schema_validator_for_synthesis(self):
        valid_data = self._valid_synthesis()
        error = SchemaValidator.validate_for_agent("brainstorming_synthesis", valid_data)
        assert error is None, f"Unexpected error: {error}"

    def test_schema_validator_rejects_missing_consensus(self):
        data = {
            "agreed_tech_stack": {"frontend": "React"},
            "critical_decisions": ["Decision 1"],
            "early_risks": [],
        }
        error = SchemaValidator.validate_for_agent("brainstorming_synthesis", data)
        assert error is not None, "Should reject output missing collective_consensus"


# ============================================================================
# _apply_brainstorming_perspective() merge logic
# ============================================================================

class TestApplyBrainstormingPerspective:
    """Tests for run_workflow._apply_brainstorming_perspective()."""

    def _get_helper(self):
        from run_workflow import _apply_brainstorming_perspective
        return _apply_brainstorming_perspective

    def _make_perspective_update(self, role: str) -> StateUpdate:
        perspective = BrainstormingPerspective(
            agent_role=role,
            domain_concerns=["Concern from " + role],
            preliminary_design={"design": role},
            recommended_approaches=["Approach from " + role],
        )
        return StateUpdate(
            brainstorming_artifacts=BrainstormingArtifacts(
                perspectives={role: perspective}
            )
        )

    def test_merge_single_perspective(self):
        fn = self._get_helper()
        state = create_initial_state("proj_010", "Build a todo app")
        update = self._make_perspective_update("architecture")
        state = fn(state, "brainstorming_architecture", update)
        assert "architecture" in state.brainstorming_artifacts.perspectives
        assert state.brainstorming_artifacts.perspectives["architecture"].agent_role == "architecture"

    def test_merge_multiple_perspectives_accumulates(self):
        fn = self._get_helper()
        state = create_initial_state("proj_011", "Build a todo app")

        for role in ["architecture", "frontend", "backend"]:
            update = self._make_perspective_update(role)
            state = fn(state, f"brainstorming_{role}", update)

        assert len(state.brainstorming_artifacts.perspectives) == 3
        assert "architecture" in state.brainstorming_artifacts.perspectives
        assert "frontend" in state.brainstorming_artifacts.perspectives
        assert "backend" in state.brainstorming_artifacts.perspectives

    def test_merge_does_not_overwrite_other_perspectives(self):
        fn = self._get_helper()
        state = create_initial_state("proj_012", "Build a todo app")

        # Add first perspective
        update_arch = self._make_perspective_update("architecture")
        state = fn(state, "brainstorming_architecture", update_arch)

        # Add second perspective — should not remove the first
        update_fe = self._make_perspective_update("frontend")
        state = fn(state, "brainstorming_frontend", update_fe)

        assert "architecture" in state.brainstorming_artifacts.perspectives
        assert "frontend" in state.brainstorming_artifacts.perspectives

    def test_merge_preserves_existing_consensus(self):
        fn = self._get_helper()
        state = create_initial_state("proj_013", "Build a todo app")
        state.brainstorming_artifacts = BrainstormingArtifacts(
            collective_consensus="Pre-existing consensus",
        )

        update = self._make_perspective_update("qa")
        state = fn(state, "brainstorming_qa", update)

        # Consensus should still be there
        assert state.brainstorming_artifacts.collective_consensus == "Pre-existing consensus"

    def test_noop_on_none_update(self):
        fn = self._get_helper()
        state = create_initial_state("proj_014", "Build a todo app")
        original_ba = state.brainstorming_artifacts
        result = fn(state, "brainstorming_qa", None)
        assert result.brainstorming_artifacts is original_ba

    def test_noop_on_update_without_brainstorming(self):
        fn = self._get_helper()
        state = create_initial_state("proj_015", "Build a todo app")
        update = StateUpdate()  # no brainstorming_artifacts
        result = fn(state, "brainstorming_qa", update)
        assert result.brainstorming_artifacts.perspectives == {}


# ============================================================================
# _build_project_context() includes brainstorming insights
# ============================================================================

class TestBuildProjectContextBrainstorming:
    def test_context_includes_brainstorming_consensus(self):
        from agent_executor import _build_project_context
        state = create_initial_state("proj_020", "Build a todo app")
        state.brainstorming_artifacts = BrainstormingArtifacts(
            collective_consensus="Use React and FastAPI for the stack.",
            agreed_tech_stack={"frontend": "React", "backend": "FastAPI"},
            critical_decisions=["JWT auth"],
            early_risks=["API instability"],
        )
        context = _build_project_context(state)
        assert "Collective Brainstorming Insights" in context
        assert "Use React and FastAPI" in context
        assert "JWT auth" in context
        assert "API instability" in context

    def test_context_omits_brainstorming_section_when_empty(self):
        from agent_executor import _build_project_context
        state = create_initial_state("proj_021", "Build a todo app")
        context = _build_project_context(state)
        assert "Collective Brainstorming Insights" not in context

    def test_context_truncates_long_consensus(self):
        from agent_executor import _build_project_context
        state = create_initial_state("proj_022", "Build a todo app")
        state.brainstorming_artifacts = BrainstormingArtifacts(
            collective_consensus="X" * 3000,  # longer than the 2000-char truncation limit
        )
        context = _build_project_context(state)
        assert "[truncated]" in context


# ============================================================================
# BRAINSTORMING_ROLES constant in run_workflow
# ============================================================================

class TestBrainstormingRolesConstant:
    def test_brainstorming_roles_defined(self):
        from run_workflow import BRAINSTORMING_ROLES, BRAINSTORMING_SYNTHESIS_AGENT
        assert len(BRAINSTORMING_ROLES) == 6
        expected_roles = {
            "brainstorming_planning",
            "brainstorming_architecture",
            "brainstorming_frontend",
            "brainstorming_backend",
            "brainstorming_qa",
            "brainstorming_documentation",
        }
        assert set(BRAINSTORMING_ROLES) == expected_roles
        assert BRAINSTORMING_SYNTHESIS_AGENT == "brainstorming_synthesis"

    def test_brainstorming_roles_in_agent_runners(self):
        from agent_executor import AGENT_RUNNERS
        from run_workflow import BRAINSTORMING_ROLES, BRAINSTORMING_SYNTHESIS_AGENT
        for role in BRAINSTORMING_ROLES:
            assert role in AGENT_RUNNERS, f"Missing AGENT_RUNNERS entry for {role}"
        assert BRAINSTORMING_SYNTHESIS_AGENT in AGENT_RUNNERS


# ============================================================================
# AgentOutputValidator brainstorming validation
# ============================================================================

class TestAgentOutputValidatorBrainstorming:
    def test_domain_agent_valid_output_passes(self):
        from agent_validators import AgentOutputValidator
        state = create_initial_state("proj_030", "Build a todo app")
        output = {
            "agent_role": "architecture",
            "domain_concerns": ["Scalability"],
            "preliminary_design": {"pattern": "monolith"},
            "recommended_approaches": ["Use REST"],
            "risks_and_challenges": [],
            "dependencies_on_others": [],
        }
        result = AgentOutputValidator.validate("brainstorming_architecture", output, state)
        assert result.passed

    def test_domain_agent_empty_domain_concerns_is_blocking(self):
        from agent_validators import AgentOutputValidator
        state = create_initial_state("proj_031", "Build a todo app")
        output = {
            "agent_role": "architecture",
            "domain_concerns": [],  # empty — should be blocking
            "preliminary_design": {"pattern": "monolith"},
            "recommended_approaches": ["Use REST"],
            "risks_and_challenges": [],
            "dependencies_on_others": [],
        }
        result = AgentOutputValidator.validate("brainstorming_architecture", output, state)
        assert not result.passed
        assert result.has_blocking_issues

    def test_domain_agent_empty_preliminary_design_is_blocking(self):
        from agent_validators import AgentOutputValidator
        state = create_initial_state("proj_032", "Build a todo app")
        output = {
            "agent_role": "frontend",
            "domain_concerns": ["Concern A"],
            "preliminary_design": {},  # empty — should be blocking
            "recommended_approaches": ["Use React"],
            "risks_and_challenges": [],
            "dependencies_on_others": [],
        }
        result = AgentOutputValidator.validate("brainstorming_frontend", output, state)
        assert not result.passed
        assert result.has_blocking_issues

    def test_synthesis_valid_output_passes(self):
        from agent_validators import AgentOutputValidator
        state = create_initial_state("proj_033", "Build a todo app")
        output = {
            "collective_consensus": "Agreed on React + FastAPI.",
            "agreed_tech_stack": {"frontend": "React", "backend": "FastAPI"},
            "critical_decisions": ["JWT auth"],
            "early_risks": [],
        }
        result = AgentOutputValidator.validate("brainstorming_synthesis", output, state)
        assert result.passed

    def test_synthesis_missing_consensus_is_blocking(self):
        from agent_validators import AgentOutputValidator
        state = create_initial_state("proj_034", "Build a todo app")
        output = {
            "collective_consensus": "",  # empty — should be blocking
            "agreed_tech_stack": {"frontend": "React"},
            "critical_decisions": ["Decision 1"],
            "early_risks": [],
        }
        result = AgentOutputValidator.validate("brainstorming_synthesis", output, state)
        assert not result.passed
        assert result.has_blocking_issues

    def test_synthesis_empty_tech_stack_is_non_blocking_warning(self):
        from agent_validators import AgentOutputValidator
        state = create_initial_state("proj_035", "Build a todo app")
        output = {
            "collective_consensus": "Valid consensus text here.",
            "agreed_tech_stack": {},  # empty — should be warning, not blocking
            "critical_decisions": ["Decision 1"],
            "early_risks": [],
        }
        result = AgentOutputValidator.validate("brainstorming_synthesis", output, state)
        # Should pass (no blocking issues) but have warnings
        assert result.passed
        non_blocking = [i for i in result.issues if not i.blocking]
        assert any("agreed_tech_stack" in i.field for i in non_blocking)


# ============================================================================
# Constants module
# ============================================================================

class TestBrainstormingConstants:
    def test_constants_defined(self):
        from config.constants import (
            BRAINSTORMING_MAX_TOKENS,
            BRAINSTORMING_SYNTHESIS_MAX_TOKENS,
            BRAINSTORMING_TEMPERATURE,
            BRAINSTORMING_ROLES,
        )
        assert BRAINSTORMING_MAX_TOKENS == 2048
        assert BRAINSTORMING_SYNTHESIS_MAX_TOKENS == 3000
        assert BRAINSTORMING_TEMPERATURE == 0.5
        assert len(BRAINSTORMING_ROLES) == 6

    def test_brainstorming_temperature_higher_than_default(self):
        from config.constants import BRAINSTORMING_TEMPERATURE
        # Brainstorming uses higher temperature for creativity
        assert BRAINSTORMING_TEMPERATURE > 0.3
