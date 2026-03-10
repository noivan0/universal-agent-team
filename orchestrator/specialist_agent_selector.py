"""
Specialist Agent Selector Module for Phase 4+

This module implements a complexity-based system for selecting optional specialist
agents during the orchestration workflow. Specialist agents are invoked only when
needed based on project complexity and specific factors.

Uses Strategy Pattern for cleaner, more testable selection logic.

Specialist Agents Available:
- Contract Validator (Agent 07): API contract validation
- Component Designer (Agent 08): UI component architecture
- Data Modeler (Agent 09): Database schema optimization
- Security Reviewer (Agent 10): Security and compliance review
- Performance Reviewer (Agent 11): Performance bottleneck analysis
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class AgentComplexity(Enum):
    """Complexity levels for specialist agent invocation."""

    LOW = 1
    MEDIUM = 2
    MEDIUM_HIGH = 3
    HIGH = 4
    VERY_HIGH = 5


class SpecialistAgentType(Enum):
    """Types of specialist agents available."""

    CONTRACT_VALIDATOR = "contract_validator"
    COMPONENT_DESIGNER = "component_designer"
    DATA_MODELER = "data_modeler"
    SECURITY_REVIEWER = "security_reviewer"
    PERFORMANCE_REVIEWER = "performance_reviewer"


@dataclass
class SpecialistAgent:
    """Definition of a specialist agent with invocation criteria."""

    agent_id: str
    agent_name: str
    agent_type: SpecialistAgentType
    role: str
    description: str
    min_complexity: int = 50
    min_complexity_level: AgentComplexity = AgentComplexity.MEDIUM
    required_factors: List[str] = field(default_factory=list)
    optional_factors: List[str] = field(default_factory=list)
    conflicting_agents: Set[str] = field(default_factory=set)
    estimated_duration_seconds: int = 120
    api_calls_required: int = 1
    enabled: bool = True

    def __post_init__(self):
        """Validate specialist agent definition."""
        if self.min_complexity < 1 or self.min_complexity > 100:
            raise ValueError("min_complexity must be between 1-100")

        if not self.agent_id:
            raise ValueError("agent_id cannot be empty")


@dataclass
class ComplexityFactors:
    """Factors that influence complexity and specialist invocation."""

    has_api: bool = False
    has_microservices: bool = False
    has_ui_heavy: bool = False
    has_database_heavy: bool = False
    has_real_time: bool = False
    has_high_load: bool = False
    requires_auth: bool = False
    requires_compliance: bool = False
    requires_performance: bool = False
    requires_scalability: bool = False
    requires_analytics: bool = False
    component_count: int = 0
    table_count: int = 0
    api_endpoint_count: int = 0
    expected_users: Optional[int] = None
    expected_concurrent_users: Optional[int] = None
    global_user_base: bool = False
    sensitive_data_types: List[str] = field(default_factory=list)
    custom_factors: Dict[str, Any] = field(default_factory=dict)

    def as_keywords(self) -> List[str]:
        """Convert factors to keyword list for text matching."""
        keywords = []

        if self.has_api:
            keywords.extend(["api", "apis", "rest", "graphql", "grpc"])
        if self.has_microservices:
            keywords.extend(["microservice", "microservices", "distributed"])
        if self.has_ui_heavy:
            keywords.extend(["ui", "frontend", "component", "design_system", "interface"])
        if self.has_database_heavy:
            keywords.extend(["database", "data", "schema"])
        if self.has_real_time:
            keywords.extend(["real-time", "real time", "realtime", "live"])
        if self.has_high_load:
            keywords.extend(["high-load", "high load", "high-traffic", "traffic"])
        if self.requires_auth:
            keywords.extend(["auth", "authentication", "oauth", "jwt"])
        if self.requires_compliance:
            keywords.extend(["gdpr", "hipaa", "soc2", "compliance", "regulation"])
        if self.requires_performance:
            keywords.extend(["performance", "latency", "throughput", "scalable"])
        if self.requires_analytics:
            keywords.extend(["analytics", "reporting", "analysis"])

        if self.sensitive_data_types:
            keywords.extend([f"{dtype.lower()}" for dtype in self.sensitive_data_types])

        return keywords

    def calculate_score(self) -> int:
        """
        Calculate composite factor score (0-100).

        Combines individual factors to determine overall project complexity
        beyond just the explicit complexity_score.
        """
        score = 0

        # API and architecture factors
        if self.has_api:
            score += 10
        if self.has_microservices:
            score += 15
        if self.has_ui_heavy and self.component_count > 10:
            score += 12

        # Data factors
        if self.has_database_heavy and self.table_count >= 5:
            score += 15
        if self.requires_analytics:
            score += 10

        # Performance and scale factors
        if self.has_real_time:
            score += 15
        if self.has_high_load:
            score += 15
        if self.requires_scalability:
            score += 12
        if self.global_user_base:
            score += 10
        if self.expected_concurrent_users and self.expected_concurrent_users > 10000:
            score += 15

        # Security and compliance factors
        if self.requires_auth:
            score += 10
        if self.requires_compliance:
            score += 15
        if self.sensitive_data_types:
            score += min(len(self.sensitive_data_types) * 5, 20)

        # Cap at 100
        return min(score, 100)


class SpecialistAgentRegistry:
    """Registry of available specialist agents."""

    def __init__(self):
        """Initialize specialist agent registry with all Phase 4 agents."""
        self.agents: Dict[str, SpecialistAgent] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Register all specialist agents."""

        # Contract Validator Agent (07)
        self.register(
            SpecialistAgent(
                agent_id="contract_validator_001",
                agent_name="Contract Validator",
                agent_type=SpecialistAgentType.CONTRACT_VALIDATOR,
                role="API Contract Validation",
                description=(
                    "Validates API contracts, request/response schemas, and "
                    "integration contracts. Ensures consistency, backwards compatibility, "
                    "and adherence to REST/GraphQL best practices."
                ),
                min_complexity=50,
                min_complexity_level=AgentComplexity.MEDIUM,
                required_factors=["has_api"],
                optional_factors=[
                    "has_microservices",
                    "requires_compliance",
                ],
                estimated_duration_seconds=120,
            )
        )

        # Component Designer Agent (08)
        self.register(
            SpecialistAgent(
                agent_id="component_designer_001",
                agent_name="Component Designer",
                agent_type=SpecialistAgentType.COMPONENT_DESIGNER,
                role="Component Architecture Design",
                description=(
                    "Reviews and enhances component architecture, optimizing for "
                    "reusability, composition patterns, and performance. Designs "
                    "shared component libraries and design systems."
                ),
                min_complexity=60,
                min_complexity_level=AgentComplexity.MEDIUM_HIGH,
                required_factors=["has_ui_heavy"],
                optional_factors=[],
                estimated_duration_seconds=120,
            )
        )

        # Data Modeler Agent (09)
        self.register(
            SpecialistAgent(
                agent_id="data_modeler_001",
                agent_name="Data Modeler",
                agent_type=SpecialistAgentType.DATA_MODELER,
                role="Database Schema & Data Model Optimization",
                description=(
                    "Reviews and optimizes database schema design, data models, "
                    "and query patterns. Validates normalization, identifies "
                    "optimization opportunities, and designs data access patterns."
                ),
                min_complexity=65,
                min_complexity_level=AgentComplexity.MEDIUM_HIGH,
                required_factors=["has_database_heavy"],
                optional_factors=[
                    "requires_scalability",
                    "requires_performance",
                ],
                estimated_duration_seconds=150,
            )
        )

        # Security Reviewer Agent (10)
        self.register(
            SpecialistAgent(
                agent_id="security_reviewer_001",
                agent_name="Security Reviewer",
                agent_type=SpecialistAgentType.SECURITY_REVIEWER,
                role="Security & Compliance Review",
                description=(
                    "Conducts comprehensive security reviews, identifying vulnerabilities, "
                    "compliance gaps, and recommending security hardening. Covers "
                    "authentication, authorization, data protection, and regulatory compliance."
                ),
                min_complexity=55,
                min_complexity_level=AgentComplexity.MEDIUM,
                required_factors=[],
                optional_factors=[
                    "requires_auth",
                    "requires_compliance",
                    "has_api",
                    "sensitive_data_types",
                ],
                estimated_duration_seconds=180,
            )
        )

        # Performance Reviewer Agent (11)
        self.register(
            SpecialistAgent(
                agent_id="performance_reviewer_001",
                agent_name="Performance Reviewer",
                agent_type=SpecialistAgentType.PERFORMANCE_REVIEWER,
                role="Performance & Scalability Analysis",
                description=(
                    "Analyzes system architecture for performance optimization, "
                    "identifying bottlenecks and recommending scaling strategies. "
                    "Focuses on response times, throughput, and end-user experience."
                ),
                min_complexity=70,
                min_complexity_level=AgentComplexity.HIGH,
                required_factors=[],
                optional_factors=[
                    "has_real_time",
                    "has_high_load",
                    "requires_scalability",
                    "requires_performance",
                ],
                estimated_duration_seconds=150,
            )
        )

    def register(self, agent: SpecialistAgent) -> None:
        """
        Register a specialist agent.

        Args:
            agent: SpecialistAgent instance to register

        Raises:
            ValueError: If agent_id already exists
        """
        if agent.agent_id in self.agents:
            raise ValueError(f"Agent {agent.agent_id} already registered")

        self.agents[agent.agent_id] = agent
        logger.info(f"Registered specialist agent: {agent.agent_name} ({agent.agent_id})")

    def get_agent(self, agent_id: str) -> Optional[SpecialistAgent]:
        """
        Retrieve a specialist agent by ID.

        Args:
            agent_id: Unique agent identifier

        Returns:
            SpecialistAgent if found, None otherwise
        """
        return self.agents.get(agent_id)

    def get_agents_by_type(
        self, agent_type: SpecialistAgentType
    ) -> List[SpecialistAgent]:
        """
        Get all agents of a specific type.

        Args:
            agent_type: Type of specialist agent

        Returns:
            List of matching agents
        """
        return [a for a in self.agents.values() if a.agent_type == agent_type]

    def list_all_agents(self) -> List[SpecialistAgent]:
        """
        Get all registered specialist agents.

        Returns:
            List of all specialist agents
        """
        return list(self.agents.values())


# ============================================================================
# Strategy Pattern Evaluators
# ============================================================================

class SpecialistEvaluator(ABC):
    """Base evaluator for specialist selection using Strategy Pattern."""

    @abstractmethod
    def evaluate(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> bool:
        """
        Evaluate if specialist should be selected.

        Args:
            specialist: SpecialistAgent to evaluate
            complexity_score: Project complexity score (1-100)
            factors: Complexity factors

        Returns:
            True if specialist meets criteria
        """
        pass

    def get_explanation(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> str:
        """
        Get explanation for evaluation decision.

        Args:
            specialist: SpecialistAgent being evaluated
            complexity_score: Project complexity score
            factors: Complexity factors

        Returns:
            Human-readable explanation
        """
        return f"{self.__class__.__name__}: evaluated"


class ComplexityThresholdEvaluator(SpecialistEvaluator):
    """Evaluate based on minimum complexity threshold."""

    def evaluate(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> bool:
        """Check if complexity meets minimum threshold."""
        return complexity_score >= specialist.min_complexity

    def get_explanation(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> str:
        """Explain complexity threshold check."""
        result = self.evaluate(specialist, complexity_score, factors)
        return (
            f"Complexity: {complexity_score} >= {specialist.min_complexity}? "
            f"{result}"
        )


class RequiredFactorsEvaluator(SpecialistEvaluator):
    """Evaluate based on required complexity factors."""

    def evaluate(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> bool:
        """Check if all required factors are present."""
        if not specialist.required_factors:
            return True

        required_met = all(
            _check_factor(factors, factor) for factor in specialist.required_factors
        )
        return required_met

    def get_explanation(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> str:
        """Explain required factors check."""
        result = self.evaluate(specialist, complexity_score, factors)
        return (
            f"Required factors {specialist.required_factors}: {result}"
        )


class OptionalFactorsEvaluator(SpecialistEvaluator):
    """Evaluate based on optional complexity factors."""

    def evaluate(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> bool:
        """Check if at least one optional factor is present."""
        if not specialist.optional_factors:
            return True

        optional_met = any(
            _check_factor(factors, factor) for factor in specialist.optional_factors
        )
        return optional_met

    def get_explanation(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> str:
        """Explain optional factors check."""
        result = self.evaluate(specialist, complexity_score, factors)
        return (
            f"Optional factors {specialist.optional_factors}: {result}"
        )


class SpecializedConditionEvaluator(SpecialistEvaluator):
    """Evaluate specialized conditions based on agent type."""

    def evaluate(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> bool:
        """Check specialized conditions for specific agent types."""
        # Data Modeler: requires sufficient tables
        if specialist.agent_type == SpecialistAgentType.DATA_MODELER:
            return factors.table_count >= 5

        # Component Designer: requires sufficient components
        if specialist.agent_type == SpecialistAgentType.COMPONENT_DESIGNER:
            return factors.component_count >= 5

        # Contract Validator: requires sufficient endpoints
        if specialist.agent_type == SpecialistAgentType.CONTRACT_VALIDATOR:
            return factors.api_endpoint_count >= 3

        return True

    def get_explanation(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> str:
        """Explain specialized condition check."""
        result = self.evaluate(specialist, complexity_score, factors)
        agent_type = specialist.agent_type

        if agent_type == SpecialistAgentType.DATA_MODELER:
            return f"Tables: {factors.table_count} >= 5? {result}"
        if agent_type == SpecialistAgentType.COMPONENT_DESIGNER:
            return f"Components: {factors.component_count} >= 5? {result}"
        if agent_type == SpecialistAgentType.CONTRACT_VALIDATOR:
            return f"Endpoints: {factors.api_endpoint_count} >= 3? {result}"

        return "Specialized conditions: passed"


class SecurityReviewerEvaluator(SpecialistEvaluator):
    """Specialized evaluator for Security Reviewer agent."""

    def evaluate(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> bool:
        """Check if Security Reviewer should be invoked."""
        # Only apply security-specific logic to the security reviewer agent
        if specialist.agent_type != SpecialistAgentType.SECURITY_REVIEWER:
            return True

        # Always invoke if complexity meets threshold AND any of these are true:
        if complexity_score < specialist.min_complexity:
            return False

        # Auto-trigger conditions
        if (
            factors.requires_compliance
            or factors.requires_auth
            or factors.sensitive_data_types
            or factors.has_api
        ):
            return True

        # Otherwise check optional factors
        if specialist.optional_factors:
            return any(
                _check_factor(factors, factor)
                for factor in specialist.optional_factors
            )

        return False

    def get_explanation(
        self,
        specialist: "SpecialistAgent",
        complexity_score: int,
        factors: "ComplexityFactors",
    ) -> str:
        """Explain security reviewer evaluation."""
        result = self.evaluate(specialist, complexity_score, factors)
        reasons = []

        if factors.requires_compliance:
            reasons.append("compliance required")
        if factors.requires_auth:
            reasons.append("auth required")
        if factors.sensitive_data_types:
            reasons.append(f"sensitive data ({len(factors.sensitive_data_types)})")
        if factors.has_api:
            reasons.append("has API")

        reason_str = ", ".join(reasons) if reasons else "no triggers"
        return f"Security review: {reason_str} → {result}"


def _check_factor(factors: "ComplexityFactors", factor_name: str) -> bool:
    """
    Check if a specific complexity factor is present.

    Args:
        factors: ComplexityFactors instance
        factor_name: Name of factor to check

    Returns:
        True if factor is present
    """
    factor_name = factor_name.lower()

    # Direct attribute checks
    if hasattr(factors, factor_name):
        value = getattr(factors, factor_name)
        return bool(value)

    # Custom factor checks
    if factor_name in factors.custom_factors:
        return bool(factors.custom_factors[factor_name])

    # String pattern matching for flexible factor checking
    keywords = factors.as_keywords()
    return any(factor_name in kw or kw in factor_name for kw in keywords)


# ============================================================================
# Simplified Selector Using Strategy Pattern
# ============================================================================

class ComplexityBasedSelector:
    """
    Selects appropriate specialist agents based on project complexity
    and complexity factors.

    Uses Strategy Pattern for cleaner, more testable evaluation logic.
    """

    def __init__(self, registry: Optional[SpecialistAgentRegistry] = None):
        """
        Initialize selector with agent registry.

        Args:
            registry: SpecialistAgentRegistry instance. If None, creates default.
        """
        self.registry = registry or SpecialistAgentRegistry()

        # Initialize evaluators (Strategy Pattern)
        self.evaluators: List[SpecialistEvaluator] = [
            ComplexityThresholdEvaluator(),
            RequiredFactorsEvaluator(),
            OptionalFactorsEvaluator(),
            SpecializedConditionEvaluator(),
            SecurityReviewerEvaluator(),
        ]

    def select_specialists(
        self,
        complexity_score: int,
        factors: ComplexityFactors,
        exclude_agents: Optional[List[str]] = None,
    ) -> List[SpecialistAgent]:
        """
        Select applicable specialist agents based on complexity and factors.

        Args:
            complexity_score: Overall project complexity (1-100)
            factors: ComplexityFactors with project characteristics
            exclude_agents: Agent IDs to exclude from selection

        Returns:
            List of selected specialist agents, ordered by priority

        Raises:
            ValueError: If complexity_score outside valid range
        """
        if not (1 <= complexity_score <= 100):
            raise ValueError("complexity_score must be between 1-100")

        exclude_agents = exclude_agents or []
        selected: List[SpecialistAgent] = []

        # Get all available agents
        candidates = [
            a
            for a in self.registry.list_all_agents()
            if a.enabled and a.agent_id not in exclude_agents
        ]

        logger.info(
            f"Selecting specialists for complexity_score={complexity_score}, "
            f"factor_score={factors.calculate_score()}"
        )

        # Evaluate each candidate agent using all evaluators
        for agent in candidates:
            if self._should_invoke_agent(complexity_score, factors, agent):
                selected.append(agent)
                logger.info(f"Selected specialist: {agent.agent_name}")
            else:
                logger.debug(f"Skipped specialist: {agent.agent_name}")

        # Remove conflicting agents (keep higher priority)
        selected = self._resolve_conflicts(selected)

        # Sort by priority (data → security → performance → api → component)
        selected = self._sort_by_priority(selected)

        logger.info(f"Final specialist selection: {len(selected)} agents")
        for agent in selected:
            logger.info(f"  - {agent.agent_name} ({agent.agent_id})")

        return selected

    def _should_invoke_agent(
        self,
        complexity_score: int,
        factors: ComplexityFactors,
        agent: SpecialistAgent,
    ) -> bool:
        """
        Determine if a specialist agent should be invoked.

        Uses all registered evaluators to make decision. All evaluators
        must return True for agent to be selected.

        Args:
            complexity_score: Project complexity (1-100)
            factors: Complexity factors
            agent: Specialist agent to evaluate

        Returns:
            True if agent should be invoked
        """
        for evaluator in self.evaluators:
            if not evaluator.evaluate(agent, complexity_score, factors):
                explanation = evaluator.get_explanation(agent, complexity_score, factors)
                logger.debug(f"{agent.agent_name}: {explanation}")
                return False

        return True


    def _resolve_conflicts(self, agents: List[SpecialistAgent]) -> List[SpecialistAgent]:
        """
        Remove conflicting agents, keeping higher priority ones.

        Args:
            agents: List of selected agents

        Returns:
            List with conflicts resolved
        """
        if not agents:
            return agents

        resolved = []
        excluded_ids = set()

        # Sort by complexity threshold (higher = higher priority)
        agents_sorted = sorted(agents, key=lambda a: a.min_complexity, reverse=True)

        for agent in agents_sorted:
            if agent.agent_id in excluded_ids:
                continue

            resolved.append(agent)

            # Exclude conflicting agents
            for conflict_id in agent.conflicting_agents:
                excluded_ids.add(conflict_id)
                logger.debug(
                    f"{agent.agent_name} conflicts with {conflict_id}, excluding"
                )

        return resolved

    def _sort_by_priority(self, agents: List[SpecialistAgent]) -> List[SpecialistAgent]:
        """
        Sort agents by execution priority.

        Execution order:
        1. Data Modeler (affects backend most)
        2. Security Reviewer (affects all layers)
        3. Contract Validator (affects backend)
        4. Component Designer (affects frontend)
        5. Performance Reviewer (last, reviews all)

        Args:
            agents: List of agents to sort

        Returns:
            Sorted list by execution priority
        """
        priority_map = {
            SpecialistAgentType.DATA_MODELER: 1,
            SpecialistAgentType.SECURITY_REVIEWER: 2,
            SpecialistAgentType.CONTRACT_VALIDATOR: 3,
            SpecialistAgentType.COMPONENT_DESIGNER: 4,
            SpecialistAgentType.PERFORMANCE_REVIEWER: 5,
        }

        return sorted(agents, key=lambda a: priority_map.get(a.agent_type, 99))

    def estimate_total_duration(self, agents: List[SpecialistAgent]) -> float:
        """
        Estimate total duration for selected specialists.

        Agents can run in parallel after Architecture Agent, but typically
        run sequentially before Development Agents.

        Args:
            agents: List of selected agents

        Returns:
            Estimated total duration in seconds (assumes parallelization)
        """
        if not agents:
            return 0

        # All agents can run in parallel, so use max duration
        return max(a.estimated_duration_seconds for a in agents)

    def estimate_api_calls(self, agents: List[SpecialistAgent]) -> int:
        """
        Estimate total API calls needed for selected specialists.

        Args:
            agents: List of selected agents

        Returns:
            Total API calls needed
        """
        return sum(a.api_calls_required for a in agents)


class SelectionResult:
    """Result of specialist agent selection."""

    def __init__(
        self,
        selected_agents: List[SpecialistAgent],
        complexity_score: int,
        factor_score: int,
        timestamp: Optional[datetime] = None,
    ):
        """
        Initialize selection result.

        Args:
            selected_agents: List of selected specialist agents
            complexity_score: Project complexity score
            factor_score: Computed factor score
            timestamp: When selection was made
        """
        self.selected_agents = selected_agents
        self.complexity_score = complexity_score
        self.factor_score = factor_score
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert selection result to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "complexity_score": self.complexity_score,
            "factor_score": self.factor_score,
            "selected_agents": len(self.selected_agents),
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "agent_name": a.agent_name,
                    "agent_type": a.agent_type.value,
                    "role": a.role,
                    "estimated_duration": a.estimated_duration_seconds,
                }
                for a in self.selected_agents
            ],
        }

    def __repr__(self) -> str:
        """String representation of selection result."""
        agent_names = [a.agent_name for a in self.selected_agents]
        return (
            f"SelectionResult(complexity={self.complexity_score}, "
            f"factors={self.factor_score}, agents={agent_names})"
        )


def create_default_selector() -> ComplexityBasedSelector:
    """
    Create a selector with default agent registry.

    Returns:
        ComplexityBasedSelector configured with all Phase 4 specialists
    """
    registry = SpecialistAgentRegistry()
    return ComplexityBasedSelector(registry)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Create selector
    selector = create_default_selector()

    # Example 1: E-commerce platform
    print("\n=== Example 1: E-commerce Platform ===")
    factors_ecom = ComplexityFactors(
        has_api=True,
        has_database_heavy=True,
        requires_auth=True,
        requires_compliance=True,
        has_ui_heavy=True,
        requires_scalability=True,
        component_count=25,
        table_count=12,
        api_endpoint_count=30,
        sensitive_data_types=["PII", "Payment Info"],
    )

    specialists_ecom = selector.select_specialists(
        complexity_score=78, factors=factors_ecom
    )

    print(f"Selected {len(specialists_ecom)} specialists:")
    for agent in specialists_ecom:
        print(f"  - {agent.agent_name}: {agent.description[:60]}...")

    # Example 2: Simple todo app
    print("\n=== Example 2: Simple Todo App ===")
    factors_todo = ComplexityFactors(
        has_ui_heavy=True,
        has_api=True,
        component_count=8,
        table_count=3,
        api_endpoint_count=5,
    )

    specialists_todo = selector.select_specialists(
        complexity_score=35, factors=factors_todo
    )

    print(f"Selected {len(specialists_todo)} specialists:")
    if specialists_todo:
        for agent in specialists_todo:
            print(f"  - {agent.agent_name}")
    else:
        print("  (No specialists needed for low-complexity project)")

    # Example 3: Real-time analytics platform
    print("\n=== Example 3: Real-time Analytics Platform ===")
    factors_analytics = ComplexityFactors(
        has_api=True,
        has_database_heavy=True,
        has_real_time=True,
        has_high_load=True,
        requires_performance=True,
        requires_scalability=True,
        expected_concurrent_users=50000,
        global_user_base=True,
        api_endpoint_count=20,
        table_count=15,
    )

    specialists_analytics = selector.select_specialists(
        complexity_score=85, factors=factors_analytics
    )

    print(f"Selected {len(specialists_analytics)} specialists:")
    for agent in specialists_analytics:
        print(f"  - {agent.agent_name}: {agent.role}")

    # Show execution order
    print("\nExecution order:")
    for i, agent in enumerate(specialists_analytics, 1):
        print(f"  {i}. {agent.agent_name} (~{agent.estimated_duration_seconds}s)")

    # Estimate totals
    total_duration = selector.estimate_total_duration(specialists_analytics)
    total_api_calls = selector.estimate_api_calls(specialists_analytics)
    print(f"\nEstimated duration: {total_duration}s")
    print(f"Estimated API calls: {total_api_calls}")
