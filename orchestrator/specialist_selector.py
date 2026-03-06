"""
Specialist Agent Selection System

Intelligently selects specialized agents based on project characteristics.
Each specialist only invoked when truly needed to optimize costs and time.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class SpecialistAgent:
    """Definition of a specialist agent."""
    name: str
    description: str
    activation_threshold: int  # Minimum complexity score to activate
    required_factors: List[str]  # Factors that trigger activation
    cost_impact: str  # Low, Medium, High
    estimated_time_minutes: int


@dataclass
class SelectionCriteria:
    """Criteria for specialist selection."""
    complexity_score: int
    complexity_factors: List[str]
    project_id: str
    team_size: int
    api_endpoint_count: int = 0


class SpecialistAgentSelector:
    """Selects appropriate specialist agents for a project."""

    SPECIALISTS = {
        'contract_validator': SpecialistAgent(
            name="Contract Validator",
            description="Validates API contracts between frontend/backend, ensures type safety",
            activation_threshold=60,
            required_factors=['api-integration', 'high-load'],
            cost_impact="Low",
            estimated_time_minutes=2
        ),
        'component_designer': SpecialistAgent(
            name="Component Designer",
            description="Designs complex React component architecture, optimizes re-renders",
            activation_threshold=70,
            required_factors=['visualization'],
            cost_impact="Medium",
            estimated_time_minutes=3
        ),
        'data_modeler': SpecialistAgent(
            name="Data Modeler",
            description="Designs normalized database schema with indexing and optimization",
            activation_threshold=75,
            required_factors=[],  # Always triggered if complexity > 75
            cost_impact="Medium",
            estimated_time_minutes=3
        ),
        'security_reviewer': SpecialistAgent(
            name="Security Reviewer",
            description="Reviews authentication, data encryption, payment security, multi-tenancy isolation",
            activation_threshold=65,
            required_factors=['authentication', 'payment', 'multi-tenant'],
            cost_impact="High",
            estimated_time_minutes=2
        ),
        'performance_reviewer': SpecialistAgent(
            name="Performance Reviewer",
            description="Analyzes performance for real-time updates, caching strategies, high concurrency",
            activation_threshold=75,
            required_factors=['real-time', 'high-load'],
            cost_impact="High",
            estimated_time_minutes=2
        ),
        'ml_specialist': SpecialistAgent(
            name="ML Specialist",
            description="Implements machine learning models, training pipelines, inference optimization",
            activation_threshold=80,
            required_factors=['machine-learning'],
            cost_impact="High",
            estimated_time_minutes=4
        ),
    }

    def select_specialists(self, criteria: SelectionCriteria) -> List[SpecialistAgent]:
        """
        Select specialists based on project characteristics.

        Args:
            criteria: Project selection criteria

        Returns:
            List of selected specialist agents
        """
        selected = []

        for specialist_key, specialist in self.SPECIALISTS.items():
            if self._should_activate(specialist, criteria):
                selected.append(specialist)

        # Sort by estimated time (longer tasks first for better parallelization)
        selected.sort(key=lambda x: x.estimated_time_minutes, reverse=True)

        return selected

    def _should_activate(self, specialist: SpecialistAgent, criteria: SelectionCriteria) -> bool:
        """Determine if specialist should be activated."""
        # Must meet minimum complexity threshold
        if criteria.complexity_score < specialist.activation_threshold:
            return False

        # If no required factors specified, activated by score alone
        if not specialist.required_factors:
            return True

        # Check if any required factors are present
        return any(factor in criteria.complexity_factors for factor in specialist.required_factors)

    def estimate_total_time(self, specialists: List[SpecialistAgent]) -> Dict[str, int]:
        """
        Estimate total execution time with parallelization.

        Args:
            specialists: Selected specialist agents

        Returns:
            Dict with sequential, parallel, and total times
        """
        if not specialists:
            return {
                'sequential_min': 2,
                'specialist_parallel_min': 0,
                'total_min': 15  # Core agents only
            }

        # All specialists run in parallel
        max_specialist_time = max(s.estimated_time_minutes for s in specialists)

        # Core pipeline: 2 (planning) + 3 (arch) + 2 (validation) + 5 (frontend) + 5 (backend) + 3 (qa) + 2 (docs)
        core_time = 22

        total = core_time + max_specialist_time

        return {
            'sequential_min': 2,  # Planning
            'architecture_min': 3,
            'specialist_parallel_min': max_specialist_time,
            'dev_parallel_min': 5,  # Max of frontend/backend
            'qa_min': 3,
            'docs_min': 2,
            'total_min': total
        }

    def get_cost_estimate(self, specialists: List[SpecialistAgent]) -> Dict[str, str]:
        """Estimate implementation cost."""
        specialist_costs = {
            'Low': 1,
            'Medium': 2,
            'High': 3,
        }

        total_cost_units = sum(specialist_costs.get(s.cost_impact, 1) for s in specialists)

        # Base cost: $5000
        # Each specialist: $2000-6000
        base = 5000
        specialist_total = total_cost_units * 2000

        return {
            'base_implementation': f"${base:,}",
            'specialist_services': f"${specialist_total:,}",
            'estimated_total': f"${base + specialist_total:,}",
            'notes': f"{len(specialists)} specialists required"
        }

    def get_summary(self, criteria: SelectionCriteria, specialists: List[SpecialistAgent]) -> str:
        """Get human-readable summary of specialist selection."""
        lines = [
            f"\n{'='*70}",
            f"SPECIALIST SELECTION SUMMARY",
            f"{'='*70}",
            f"Project ID: {criteria.project_id}",
            f"Complexity Score: {criteria.complexity_score}/100",
            f"Complexity Factors: {', '.join(criteria.complexity_factors) or 'None'}",
            f"",
            f"SPECIALISTS SELECTED: {len(specialists)}",
        ]

        if specialists:
            for specialist in specialists:
                lines.append(f"  ✓ {specialist.name} ({specialist.estimated_time_minutes} min)")
                lines.append(f"    {specialist.description}")
        else:
            lines.append("  (None - project has low complexity)")

        time_est = self.estimate_total_time(specialists)
        lines.extend([
            f"",
            f"EXECUTION ESTIMATE:",
            f"  Total time: ~{time_est['total_min']} minutes (with parallelization)",
            f"  Sequential pipeline: {time_est['sequential_min']} + {time_est['architecture_min']} + 2 (validation)",
            f"  Parallel specialists: {time_est['specialist_parallel_min']} min",
            f"  Dev teams (parallel): {time_est['dev_parallel_min']} min",
            f"  QA + Docs: {time_est['qa_min']} + {time_est['docs_min']} min",
        ])

        cost = self.get_cost_estimate(specialists)
        lines.extend([
            f"",
            f"COST ESTIMATE:",
            f"  Base implementation: {cost['base_implementation']}",
            f"  Specialist services: {cost['specialist_services']}",
            f"  Total: {cost['estimated_total']}",
            f"  {cost['notes']}",
            f"{'='*70}\n",
        ])

        return "\n".join(lines)
