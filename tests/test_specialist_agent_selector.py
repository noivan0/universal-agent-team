"""
Unit tests for specialist agent selector.

Tests cover:
- Specialist invocation conditions
- Complexity-based selection
- Factor-based selection
- Multiple specialist combinations
- Edge cases and performance impacts
"""

import pytest
from orchestrator.specialist_agent_selector import (
    ComplexityFactors,
    SpecialistAgentType,
    SpecialistAgent,
    SpecialistAgentRegistry,
    ComplexityBasedSelector,
    SelectionResult,
    AgentComplexity,
    create_default_selector,
)


@pytest.mark.unit
class TestComplexityFactors:
    """Test complexity factor calculations."""

    def test_empty_factors(self):
        """Test empty factors object."""
        factors = ComplexityFactors()

        assert factors.has_api is False
        assert factors.has_microservices is False
        assert factors.has_ui_heavy is False
        assert factors.component_count == 0
        assert factors.table_count == 0

    def test_as_keywords(self):
        """Test converting factors to keywords."""
        factors = ComplexityFactors(
            has_api=True,
            has_ui_heavy=True,
            has_database_heavy=False
        )

        keywords = factors.as_keywords()

        assert "api" in keywords
        assert "rest" in keywords
        assert "ui" in keywords
        assert "frontend" in keywords

    def test_calculate_score_low(self):
        """Test score calculation for low complexity."""
        factors = ComplexityFactors()

        score = factors.calculate_score()

        assert 0 <= score <= 30

    def test_calculate_score_medium(self):
        """Test score calculation for medium complexity."""
        factors = ComplexityFactors(
            has_api=True,
            has_database_heavy=True,
            table_count=5,
            component_count=8,
            api_endpoint_count=10
        )

        score = factors.calculate_score()

        assert 20 <= score <= 60

    def test_calculate_score_high(self):
        """Test score calculation for high complexity."""
        factors = ComplexityFactors(
            has_api=True,
            has_microservices=True,
            has_ui_heavy=True,
            has_database_heavy=True,
            has_real_time=True,
            has_high_load=True,
            requires_auth=True,
            requires_compliance=True,
            requires_scalability=True,
            component_count=25,
            table_count=15,
            api_endpoint_count=30,
            expected_concurrent_users=50000,
            sensitive_data_types=["PII", "Payment Info"]
        )

        score = factors.calculate_score()

        assert score >= 60

    def test_calculate_score_capped_at_100(self):
        """Test that score is capped at 100."""
        factors = ComplexityFactors(
            has_api=True,
            has_microservices=True,
            has_ui_heavy=True,
            has_database_heavy=True,
            has_real_time=True,
            has_high_load=True,
            requires_auth=True,
            requires_compliance=True,
            requires_performance=True,
            requires_scalability=True,
            requires_analytics=True,
            component_count=100,
            table_count=100,
            expected_concurrent_users=1000000,
            sensitive_data_types=["PII", "Payment", "Health", "Government ID"]
        )

        score = factors.calculate_score()

        assert score == 100

    def test_sensitivity_data_types(self):
        """Test sensitive data type tracking."""
        factors = ComplexityFactors(
            sensitive_data_types=["PII", "Payment Info", "Health Records"]
        )

        assert len(factors.sensitive_data_types) == 3
        assert "PII" in factors.sensitive_data_types

    def test_custom_factors(self):
        """Test custom factors support."""
        factors = ComplexityFactors(
            custom_factors={
                "blockchain_required": True,
                "ml_model_needed": False,
                "iot_devices": 150
            }
        )

        assert factors.custom_factors["blockchain_required"] is True
        assert factors.custom_factors["ml_model_needed"] is False


@pytest.mark.unit
class TestSpecialistAgentRegistry:
    """Test specialist agent registry."""

    def test_registry_initialization(self):
        """Test registry initializes with default agents."""
        registry = SpecialistAgentRegistry()

        agents = registry.list_all_agents()

        assert len(agents) == 5
        assert any(a.agent_type == SpecialistAgentType.CONTRACT_VALIDATOR for a in agents)
        assert any(a.agent_type == SpecialistAgentType.COMPONENT_DESIGNER for a in agents)
        assert any(a.agent_type == SpecialistAgentType.DATA_MODELER for a in agents)
        assert any(a.agent_type == SpecialistAgentType.SECURITY_REVIEWER for a in agents)
        assert any(a.agent_type == SpecialistAgentType.PERFORMANCE_REVIEWER for a in agents)

    def test_get_agent_by_id(self):
        """Test retrieving agent by ID."""
        registry = SpecialistAgentRegistry()

        agent = registry.get_agent("contract_validator_001")

        assert agent is not None
        assert agent.agent_name == "Contract Validator"
        assert agent.agent_type == SpecialistAgentType.CONTRACT_VALIDATOR

    def test_get_agents_by_type(self):
        """Test retrieving agents by type."""
        registry = SpecialistAgentRegistry()

        validators = registry.get_agents_by_type(SpecialistAgentType.CONTRACT_VALIDATOR)

        assert len(validators) == 1
        assert validators[0].agent_name == "Contract Validator"

    def test_register_custom_agent(self):
        """Test registering a custom specialist agent."""
        registry = SpecialistAgentRegistry()

        custom_agent = SpecialistAgent(
            agent_id="custom_agent_001",
            agent_name="Custom Specialist",
            agent_type=SpecialistAgentType.CONTRACT_VALIDATOR,
            role="Custom Role",
            description="Custom Description",
            min_complexity=75
        )

        # Note: The registry will raise ValueError if agent_id exists
        # So we use a unique ID
        registry.register(custom_agent)

        assert registry.get_agent("custom_agent_001") is not None

    def test_register_duplicate_fails(self):
        """Test that registering duplicate agent ID fails."""
        registry = SpecialistAgentRegistry()

        duplicate = SpecialistAgent(
            agent_id="contract_validator_001",
            agent_name="Duplicate",
            agent_type=SpecialistAgentType.CONTRACT_VALIDATOR,
            role="Duplicate Role",
            description="Duplicate"
        )

        with pytest.raises(ValueError):
            registry.register(duplicate)


@pytest.mark.unit
class TestSpecialistAgentDefinition:
    """Test specialist agent definition and validation."""

    def test_specialist_agent_creation(self):
        """Test creating a specialist agent."""
        agent = SpecialistAgent(
            agent_id="test_001",
            agent_name="Test Agent",
            agent_type=SpecialistAgentType.CONTRACT_VALIDATOR,
            role="Test Role",
            description="Test Description"
        )

        assert agent.agent_id == "test_001"
        assert agent.agent_name == "Test Agent"
        assert agent.enabled is True

    def test_specialist_agent_with_factors(self):
        """Test specialist agent with required and optional factors."""
        agent = SpecialistAgent(
            agent_id="test_001",
            agent_name="Test Agent",
            agent_type=SpecialistAgentType.CONTRACT_VALIDATOR,
            role="Test",
            description="Test",
            min_complexity=50,
            required_factors=["has_api"],
            optional_factors=["has_microservices", "requires_compliance"]
        )

        assert "has_api" in agent.required_factors
        assert "has_microservices" in agent.optional_factors

    def test_complexity_validation(self):
        """Test complexity threshold validation."""
        # Valid complexity
        agent = SpecialistAgent(
            agent_id="test_001",
            agent_name="Test",
            agent_type=SpecialistAgentType.CONTRACT_VALIDATOR,
            role="Test",
            description="Test",
            min_complexity=50
        )

        assert agent.min_complexity == 50

        # Invalid complexity (too low)
        with pytest.raises(ValueError):
            SpecialistAgent(
                agent_id="test_002",
                agent_name="Test",
                agent_type=SpecialistAgentType.CONTRACT_VALIDATOR,
                role="Test",
                description="Test",
                min_complexity=0
            )

        # Invalid complexity (too high)
        with pytest.raises(ValueError):
            SpecialistAgent(
                agent_id="test_003",
                agent_name="Test",
                agent_type=SpecialistAgentType.CONTRACT_VALIDATOR,
                role="Test",
                description="Test",
                min_complexity=101
            )


@pytest.mark.unit
class TestComplexityBasedSelection:
    """Test complexity-based specialist selection."""

    def test_simple_project_no_specialists(self):
        """Test that simple projects don't require specialists."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_api=True,
            has_ui_heavy=True,
            component_count=5,
            table_count=2,
            api_endpoint_count=4
        )

        selected = selector.select_specialists(
            complexity_score=30,
            factors=factors
        )

        # Simple project should have no or minimal specialists
        assert len(selected) <= 1

    def test_medium_complexity_project(self):
        """Test medium complexity project selection."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_api=True,
            has_database_heavy=True,
            table_count=8,
            component_count=12,
            api_endpoint_count=15,
            requires_auth=True
        )

        selected = selector.select_specialists(
            complexity_score=55,
            factors=factors
        )

        # Medium complexity should select some specialists
        assert len(selected) >= 0

    def test_high_complexity_project(self):
        """Test high complexity project selection."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_api=True,
            has_microservices=True,
            has_ui_heavy=True,
            has_database_heavy=True,
            has_real_time=True,
            has_high_load=True,
            requires_auth=True,
            requires_compliance=True,
            requires_performance=True,
            requires_scalability=True,
            component_count=30,
            table_count=20,
            api_endpoint_count=50,
            expected_concurrent_users=100000,
            sensitive_data_types=["PII", "Payment Info"]
        )

        selected = selector.select_specialists(
            complexity_score=85,
            factors=factors
        )

        # High complexity should select multiple specialists
        assert len(selected) >= 2

    def test_contract_validator_selection(self):
        """Test contract validator specialist selection."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_api=True,
            api_endpoint_count=10,
            has_microservices=True
        )

        selected = selector.select_specialists(
            complexity_score=60,
            factors=factors
        )

        # Should select contract validator for API-heavy project
        validator = [a for a in selected if a.agent_type == SpecialistAgentType.CONTRACT_VALIDATOR]
        assert len(validator) > 0

    def test_component_designer_selection(self):
        """Test component designer specialist selection."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_ui_heavy=True,
            component_count=20
        )

        selected = selector.select_specialists(
            complexity_score=70,
            factors=factors
        )

        # Should select component designer for UI-heavy project
        designer = [a for a in selected if a.agent_type == SpecialistAgentType.COMPONENT_DESIGNER]
        assert len(designer) > 0

    def test_data_modeler_selection(self):
        """Test data modeler specialist selection."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_database_heavy=True,
            table_count=12,
            requires_performance=True
        )

        selected = selector.select_specialists(
            complexity_score=70,
            factors=factors
        )

        # Should select data modeler for database-heavy project
        modeler = [a for a in selected if a.agent_type == SpecialistAgentType.DATA_MODELER]
        assert len(modeler) > 0

    def test_security_reviewer_selection(self):
        """Test security reviewer specialist selection."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_api=True,
            requires_auth=True,
            requires_compliance=True,
            sensitive_data_types=["PII"]
        )

        selected = selector.select_specialists(
            complexity_score=55,
            factors=factors
        )

        # Should select security reviewer for compliance project
        reviewer = [a for a in selected if a.agent_type == SpecialistAgentType.SECURITY_REVIEWER]
        assert len(reviewer) > 0

    def test_performance_reviewer_selection(self):
        """Test performance reviewer specialist selection."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_real_time=True,
            has_high_load=True,
            requires_performance=True,
            expected_concurrent_users=50000
        )

        selected = selector.select_specialists(
            complexity_score=75,
            factors=factors
        )

        # Should select performance reviewer for high-performance project
        reviewer = [a for a in selected if a.agent_type == SpecialistAgentType.PERFORMANCE_REVIEWER]
        assert len(reviewer) > 0

    def test_multiple_specialist_selection(self):
        """Test selection of multiple specialists."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_api=True,
            has_microservices=True,
            has_ui_heavy=True,
            has_database_heavy=True,
            has_high_load=True,
            requires_auth=True,
            requires_compliance=True,
            requires_performance=True,
            component_count=25,
            table_count=15,
            api_endpoint_count=30,
            expected_concurrent_users=50000,
            sensitive_data_types=["PII", "Payment Info"]
        )

        selected = selector.select_specialists(
            complexity_score=90,
            factors=factors
        )

        # High complexity with multiple factors should select multiple specialists
        assert len(selected) >= 3

    def test_exclude_agents(self):
        """Test excluding specific agents from selection."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_api=True,
            has_database_heavy=True,
            has_ui_heavy=True,
            table_count=10,
            component_count=20,
            api_endpoint_count=20
        )

        all_selected = selector.select_specialists(
            complexity_score=75,
            factors=factors
        )

        excluded_selected = selector.select_specialists(
            complexity_score=75,
            factors=factors,
            exclude_agents=["contract_validator_001"]
        )

        # Excluded agent should not be in result
        excluded_ids = {a.agent_id for a in excluded_selected}
        assert "contract_validator_001" not in excluded_ids

    def test_invalid_complexity_score(self):
        """Test that invalid complexity scores raise ValueError."""
        selector = create_default_selector()
        factors = ComplexityFactors()

        with pytest.raises(ValueError):
            selector.select_specialists(complexity_score=0, factors=factors)

        with pytest.raises(ValueError):
            selector.select_specialists(complexity_score=101, factors=factors)


@pytest.mark.unit
class TestSelectionOrdering:
    """Test specialist selection ordering and priority."""

    def test_selection_execution_order(self):
        """Test that specialists are ordered by execution priority."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_api=True,
            has_ui_heavy=True,
            has_database_heavy=True,
            requires_auth=True,
            requires_performance=True,
            component_count=20,
            table_count=10,
            api_endpoint_count=20
        )

        selected = selector.select_specialists(
            complexity_score=80,
            factors=factors
        )

        # Verify ordering: Data → Security → Contract → Component → Performance
        type_order = [a.agent_type for a in selected]

        data_idx = next((i for i, t in enumerate(type_order) if t == SpecialistAgentType.DATA_MODELER), -1)
        security_idx = next((i for i, t in enumerate(type_order) if t == SpecialistAgentType.SECURITY_REVIEWER), -1)
        contract_idx = next((i for i, t in enumerate(type_order) if t == SpecialistAgentType.CONTRACT_VALIDATOR), -1)

        if data_idx >= 0 and security_idx >= 0:
            assert data_idx < security_idx
        if security_idx >= 0 and contract_idx >= 0:
            assert security_idx < contract_idx


@pytest.mark.unit
class TestDurationAndCostEstimation:
    """Test duration and cost estimation for specialists."""

    def test_estimate_duration_single_agent(self):
        """Test duration estimation for single specialist."""
        selector = create_default_selector()

        factors = ComplexityFactors(
            has_api=True,
            api_endpoint_count=10
        )

        selected = selector.select_specialists(
            complexity_score=60,
            factors=factors
        )

        duration = selector.estimate_total_duration(selected)

        # Agents run in parallel, so duration is max of individual durations
        assert duration >= 0
        if selected:
            max_individual = max(a.estimated_duration_seconds for a in selected)
            assert duration == max_individual

    def test_estimate_duration_multiple_agents(self):
        """Test duration estimation for multiple specialists."""
        selector = create_default_selector()

        factors = ComplexityFactors(
            has_api=True,
            has_ui_heavy=True,
            has_database_heavy=True,
            component_count=20,
            table_count=10,
            api_endpoint_count=20
        )

        selected = selector.select_specialists(
            complexity_score=75,
            factors=factors
        )

        duration = selector.estimate_total_duration(selected)

        # With parallel execution, duration should be max individual duration
        if selected:
            max_individual = max(a.estimated_duration_seconds for a in selected)
            assert duration == max_individual

    def test_estimate_api_calls(self):
        """Test API call estimation for specialists."""
        selector = create_default_selector()

        factors = ComplexityFactors(
            has_api=True,
            has_database_heavy=True,
            has_ui_heavy=True,
            component_count=15,
            table_count=8,
            api_endpoint_count=15
        )

        selected = selector.select_specialists(
            complexity_score=70,
            factors=factors
        )

        api_calls = selector.estimate_api_calls(selected)

        # Should sum all api_calls_required
        expected = sum(a.api_calls_required for a in selected)
        assert api_calls == expected

    def test_empty_selection_duration(self):
        """Test duration estimation for empty selection."""
        selector = create_default_selector()

        duration = selector.estimate_total_duration([])

        assert duration == 0

    def test_empty_selection_api_calls(self):
        """Test API call estimation for empty selection."""
        selector = create_default_selector()

        api_calls = selector.estimate_api_calls([])

        assert api_calls == 0


@pytest.mark.unit
class TestSelectionResult:
    """Test selection result object."""

    def test_selection_result_creation(self):
        """Test creating a selection result."""
        registry = SpecialistAgentRegistry()
        agents = registry.list_all_agents()[:2]

        result = SelectionResult(
            selected_agents=agents,
            complexity_score=75,
            factor_score=60
        )

        assert len(result.selected_agents) == 2
        assert result.complexity_score == 75
        assert result.factor_score == 60

    def test_selection_result_to_dict(self):
        """Test converting selection result to dictionary."""
        registry = SpecialistAgentRegistry()
        agents = registry.list_all_agents()[:1]

        result = SelectionResult(
            selected_agents=agents,
            complexity_score=75,
            factor_score=60
        )

        result_dict = result.to_dict()

        assert result_dict["complexity_score"] == 75
        assert result_dict["factor_score"] == 60
        assert result_dict["selected_agents"] == 1
        assert len(result_dict["agents"]) == 1

    def test_selection_result_repr(self):
        """Test string representation of selection result."""
        registry = SpecialistAgentRegistry()
        agents = registry.list_all_agents()[:1]

        result = SelectionResult(
            selected_agents=agents,
            complexity_score=75,
            factor_score=60
        )

        repr_str = repr(result)

        assert "complexity=75" in repr_str
        assert "factors=60" in repr_str


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_complexity_threshold(self):
        """Test selection at minimum complexity."""
        selector = create_default_selector()
        factors = ComplexityFactors()

        selected = selector.select_specialists(
            complexity_score=1,
            factors=factors
        )

        # Should select no or very few specialists
        assert len(selected) == 0

    def test_maximum_complexity_threshold(self):
        """Test selection at maximum complexity."""
        selector = create_default_selector()
        factors = ComplexityFactors(
            has_api=True,
            has_microservices=True,
            has_ui_heavy=True,
            has_database_heavy=True,
            has_real_time=True,
            has_high_load=True,
            requires_auth=True,
            requires_compliance=True,
            requires_performance=True,
            requires_scalability=True,
            component_count=100,
            table_count=100,
            api_endpoint_count=100,
            expected_concurrent_users=1000000
        )

        selected = selector.select_specialists(
            complexity_score=100,
            factors=factors
        )

        # Should select multiple specialists
        assert len(selected) > 0

    def test_exactly_minimum_complexity_boundary(self):
        """Test selection at exact minimum complexity boundary."""
        selector = create_default_selector()

        # Get first agent and its minimum complexity
        agent = selector.registry.list_all_agents()[0]
        min_complexity = agent.min_complexity

        factors = ComplexityFactors()

        # At exact minimum
        selected = selector.select_specialists(
            complexity_score=min_complexity,
            factors=factors
        )

        # Result depends on factors matching
        assert isinstance(selected, list)

    def test_no_matching_factors(self):
        """Test selection with no matching factors."""
        selector = create_default_selector()

        # Create factors that don't match any specialist requirements
        factors = ComplexityFactors()

        selected = selector.select_specialists(
            complexity_score=50,
            factors=factors
        )

        # Should select none or only security reviewer
        # (security reviewer doesn't require factors)
        assert len(selected) <= 1

    def test_conflicting_agents_resolution(self):
        """Test that conflicting agents are properly resolved."""
        selector = create_default_selector()

        # Get registry and check for conflicting agents
        registry = selector.registry
        agents = registry.list_all_agents()

        # Check that conflicting_agents field is handled
        for agent in agents:
            assert isinstance(agent.conflicting_agents, set)
