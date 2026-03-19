"""
Dependency-based context loader for agents.

Implements intelligent context loading based on agent dependencies,
ensuring each agent only receives the information it needs while
maintaining accuracy and consistency.
"""

import logging
import threading
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from collections import OrderedDict

from state_models import AgentState, AgentPhase

logger = logging.getLogger(__name__)


# ============================================================================
# Dependency Graph Definition
# ============================================================================

class DependencyGraph:
    """
    Defines which agents depend on which other agents.

    Used by orchestrator to:
    1. Determine execution order
    2. Know when an agent can start (all dependencies completed)
    3. Load only necessary context for each agent
    4. Determine impact when an agent fails/restarts

    Features caching of execution order calculations for performance.
    """

    # Agent dependency relationships
    # Key: agent_id, Value: list of agent_ids it depends on
    DEPENDENCIES = {
        "planning": [],
        "architecture": ["planning"],
        "contract_validator": ["architecture"],
        "frontend": ["architecture", "contract_validator"],
        "backend": ["architecture", "contract_validator"],
        "qa": ["frontend", "backend"],
        "documentation": ["planning", "architecture", "frontend", "backend", "qa"]
    }

    # Reverse dependencies (who depends on this agent)
    DEPENDENTS = {
        "planning": ["architecture"],
        "architecture": ["contract_validator", "frontend", "backend"],
        "contract_validator": ["frontend", "backend"],
        "frontend": ["qa", "documentation"],
        "backend": ["qa", "documentation"],
        "qa": ["documentation"],
        "documentation": []
    }

    # Context requirements by agent
    # Maps agent -> list of required input sections
    CONTEXT_REQUIREMENTS = {
        "planning": [],
        "architecture": ["planning"],
        "contract_validator": ["architecture"],
        "frontend": ["architecture", "planning"],
        "backend": ["architecture", "planning"],
        "qa": ["development"],
        "documentation": ["planning", "architecture", "development", "testing"]
    }

    # ========== CACHING FOR EXECUTION ORDER ==========
    # Maximum size for execution order cache (LRU eviction when exceeded)
    _MAX_CACHE_SIZE = 100

    # Cache for execution order calculations (OrderedDict for LRU eviction)
    _execution_order_cache: OrderedDict[str, List[str]] = OrderedDict()
    # Lock for thread-safe cache access
    _cache_lock: threading.Lock = threading.Lock()
    # Track cache invalidation timestamps
    _cache_invalidation_timestamp: Dict[str, float] = {}

    @staticmethod
    def get_dependencies(agent_id: str) -> List[str]:
        """Get agents that this agent depends on."""
        return DependencyGraph.DEPENDENCIES.get(agent_id, [])

    @staticmethod
    def get_dependents(agent_id: str) -> List[str]:
        """Get agents that depend on this agent."""
        return DependencyGraph.DEPENDENTS.get(agent_id, [])

    @staticmethod
    def get_context_requirements(agent_id: str) -> List[str]:
        """Get required context sections for this agent."""
        return DependencyGraph.CONTEXT_REQUIREMENTS.get(agent_id, [])

    @staticmethod
    def can_execute(
        agent_id: str,
        completed_agents: Set[str]
    ) -> bool:
        """
        Check if an agent can execute (all dependencies completed).

        Args:
            agent_id: Agent to check
            completed_agents: Set of completed agent IDs

        Returns:
            True if all dependencies are satisfied
        """
        dependencies = DependencyGraph.get_dependencies(agent_id)
        return all(dep in completed_agents for dep in dependencies)

    @staticmethod
    def _get_cache_key(agents: Optional[List[str]]) -> str:
        """Generate cache key from agent list.

        Args:
            agents: List of agent IDs or None for default

        Returns:
            Cache key string
        """
        if agents is None:
            return "default_order"
        return "|".join(sorted(agents))

    @staticmethod
    def _evict_if_needed() -> None:
        """Remove oldest entry if cache exceeds max size.

        Uses LRU (Least Recently Used) eviction policy.
        Called before adding new entries to maintain bounded memory.
        """
        if len(DependencyGraph._execution_order_cache) >= DependencyGraph._MAX_CACHE_SIZE:
            oldest_key, _ = DependencyGraph._execution_order_cache.popitem(last=False)
            logger.debug(
                f"Cache evicted oldest entry: {oldest_key}. "
                f"Size: {len(DependencyGraph._execution_order_cache)}"
            )

    @staticmethod
    def get_execution_order(
        target_agents: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> List[str]:
        """
        Determine execution order for agents using topological sort.

        Caches results for performance optimization with bounded memory usage.
        Uses LRU eviction when cache size exceeds _MAX_CACHE_SIZE.

        Args:
            target_agents: Specific agents to include (default: all)
            use_cache: Whether to use cached results (default: True)

        Returns:
            List of agent IDs in valid execution order
        """
        # Check cache first
        if use_cache:
            cache_key = DependencyGraph._get_cache_key(target_agents)
            with DependencyGraph._cache_lock:
                if cache_key in DependencyGraph._execution_order_cache:
                    # Move to end (most recently used)
                    DependencyGraph._execution_order_cache.move_to_end(cache_key)
                    logger.debug(f"Cache hit for execution order: {cache_key}")
                    return DependencyGraph._execution_order_cache[cache_key].copy()

        # Perform topological sort
        target = set(target_agents or DependencyGraph.DEPENDENCIES.keys())
        order = []
        completed = set()

        while completed != target:
            for agent in target - completed:
                # Only require deps that are themselves in the target set
                deps = DependencyGraph.get_dependencies(agent)
                relevant_deps = [d for d in deps if d in target]
                if all(dep in completed for dep in relevant_deps):
                    order.append(agent)
                    completed.add(agent)
                    break
            else:
                # Circular dependency or missing dependency
                remaining = target - completed
                raise ValueError(f"Cannot resolve execution order for: {remaining}")

        # Store in cache if enabled (with LRU eviction)
        if use_cache:
            cache_key = DependencyGraph._get_cache_key(target_agents)
            with DependencyGraph._cache_lock:
                DependencyGraph._evict_if_needed()
                DependencyGraph._execution_order_cache[cache_key] = order.copy()
                logger.debug(f"Cached execution order: {cache_key} (size: {len(DependencyGraph._execution_order_cache)})")

        return order

    @staticmethod
    def invalidate_cache() -> None:
        """
        Clear execution order cache.

        Call this when team configuration changes or dependencies are updated.
        """
        with DependencyGraph._cache_lock:
            DependencyGraph._execution_order_cache.clear()
            DependencyGraph._cache_invalidation_timestamp.clear()
        logger.info("Execution order cache invalidated")

    @staticmethod
    def get_cache_stats() -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics including max size
        """
        return {
            "cached_orders": len(DependencyGraph._execution_order_cache),
            "max_cache_size": DependencyGraph._MAX_CACHE_SIZE,
            "cache_utilization_percent": int(
                100 * len(DependencyGraph._execution_order_cache) / DependencyGraph._MAX_CACHE_SIZE
            ),
            "total_entries": len(DependencyGraph._cache_invalidation_timestamp)
        }

    @staticmethod
    def get_affected_agents(failed_agent: str) -> List[str]:
        """
        Get all agents affected by failure of one agent.

        Args:
            failed_agent: Agent that failed

        Returns:
            List of agent IDs that would be affected (including failed agent)
        """
        affected = {failed_agent}
        to_check = [failed_agent]

        while to_check:
            current = to_check.pop()
            dependents = DependencyGraph.get_dependents(current)

            for dependent in dependents:
                if dependent not in affected:
                    affected.add(dependent)
                    to_check.append(dependent)

        return list(affected)


# ============================================================================
# Context Requirement Analyzer
# ============================================================================

@dataclass
class ContextRequirement:
    """A requirement for context."""
    section: str           # "planning", "architecture", "development", etc.
    is_critical: bool      # True if agent cannot proceed without it
    max_tokens: Optional[int] = None  # Maximum tokens for this section


class ContextAnalyzer:
    """Analyzes what context an agent needs."""

    @staticmethod
    def analyze_requirements(agent_id: str) -> List[ContextRequirement]:
        """
        Determine all context requirements for an agent.

        Args:
            agent_id: Agent to analyze

        Returns:
            List of context requirements
        """
        requirements = []

        # Get dependencies from graph
        dependencies = DependencyGraph.get_dependencies(agent_id)
        context_sections = DependencyGraph.get_context_requirements(agent_id)

        # Map dependencies to context sections
        section_map = {
            "planning": ["planning"],
            "architecture": ["architecture"],
            "frontend": ["development.frontend"],
            "backend": ["development.backend"],
            "qa": ["development"],
        }

        for section in context_sections:
            # Determine if critical
            is_critical = section in ["architecture", "api_specs"]

            requirements.append(ContextRequirement(
                section=section,
                is_critical=is_critical,
                max_tokens=None  # No limit by default
            ))

        # Always include metadata
        requirements.append(ContextRequirement(
            section="metadata",
            is_critical=True,
            max_tokens=1000  # Small limit for metadata
        ))

        return requirements

    @staticmethod
    def validate_context(
        state: AgentState,
        agent_id: str
    ) -> tuple[bool, List[str]]:
        """
        Validate that state has all required context for an agent.

        Args:
            state: Current state
            agent_id: Agent to validate for

        Returns:
            Tuple of (is_valid, missing_requirements)
        """
        requirements = ContextAnalyzer.analyze_requirements(agent_id)
        missing = []

        for req in requirements:
            # Check if required section exists and has content
            if req.section == "planning":
                if not state.planning_artifacts.requirements:
                    missing.append(req.section)
            elif req.section == "architecture":
                if not state.architecture_artifacts.system_design:
                    missing.append(req.section)
            elif req.section == "development":
                if (not state.development.frontend.code_files and
                    not state.development.backend.code_files):
                    missing.append(req.section)

        return len(missing) == 0, missing


# ============================================================================
# Dependency-Aware Context Loader
# ============================================================================

class DependencyContextLoader:
    """
    Loads context for agents based on their dependencies.

    Ensures minimal, targeted context loading for efficiency.
    """

    @staticmethod
    def load_context_for_agent(
        state: AgentState,
        agent_id: str,
        compress: bool = True
    ) -> Dict[str, any]:
        """
        Load minimal context needed for an agent.

        Args:
            state: Full agent state
            agent_id: Agent to load context for
            compress: Whether to compress large artifacts

        Returns:
            Context dictionary with only necessary information
        """
        context = {}

        # Always include metadata
        context["metadata"] = state.metadata.model_dump()

        # Get required sections for this agent
        required_sections = DependencyGraph.get_context_requirements(agent_id)

        # Load each required section
        if "planning" in required_sections:
            context["planning"] = state.planning_artifacts.model_dump()

        if "architecture" in required_sections:
            context["architecture"] = state.architecture_artifacts.model_dump()

        if "development" in required_sections:
            # Include both frontend and backend
            context["development"] = {
                "frontend": state.development.frontend.model_dump(),
                "backend": state.development.backend.model_dump(),
            }

        if "development.frontend" in required_sections:
            context["development"] = {"frontend": state.development.frontend.model_dump()}

        if "development.backend" in required_sections:
            context["development"] = {"backend": state.development.backend.model_dump()}

        if "testing" in required_sections:
            context["testing"] = state.testing_artifacts.model_dump()

        if "documentation" in required_sections:
            context["documentation"] = state.documentation_artifacts.model_dump()

        # Include execution status for dependency tracking
        context["execution_status"] = state.execution_status.model_dump()

        return context

    @staticmethod
    def estimate_context_size(
        state: AgentState,
        agent_id: str
    ) -> Dict[str, int]:
        """
        Estimate size of context for an agent.

        Args:
            state: Full agent state
            agent_id: Agent to estimate for

        Returns:
            Dict with size estimates {section: bytes}
        """
        import json

        sizes = {}
        required_sections = DependencyGraph.get_context_requirements(agent_id)

        for section in required_sections:
            if section == "planning":
                size = len(json.dumps(state.planning_artifacts.model_dump()))
            elif section == "architecture":
                size = len(json.dumps(state.architecture_artifacts.model_dump()))
            elif section == "development":
                size = len(json.dumps(state.development.model_dump()))
            elif section == "testing":
                size = len(json.dumps(state.testing_artifacts.model_dump()))
            elif section == "documentation":
                size = len(json.dumps(state.documentation_artifacts.model_dump()))
            else:
                size = 0

            sizes[section] = size

        return sizes

    @staticmethod
    def estimate_tokens_for_agent(
        state: AgentState,
        agent_id: str
    ) -> int:
        """
        Estimate tokens needed for an agent's context.

        Rough estimate: 1 token ≈ 4 characters.

        Args:
            state: Full agent state
            agent_id: Agent to estimate for

        Returns:
            Estimated token count
        """
        sizes = DependencyContextLoader.estimate_context_size(state, agent_id)
        total_bytes = sum(sizes.values())

        # Add metadata
        import json
        metadata_bytes = len(json.dumps(state.metadata.model_dump()))

        return (total_bytes + metadata_bytes) // 4  # Rough 4 chars per token


# ============================================================================
# Restart Impact Analysis
# ============================================================================

class RestartImpactAnalyzer:
    """
    Analyzes impact of restarting a specific agent.

    Determines which agents need to be re-executed based on restart.
    """

    @staticmethod
    def get_restart_chain(
        failed_agent: str,
        failure_type: str = "code"  # "code", "spec", or "both"
    ) -> List[str]:
        """
        Determine which agents to restart based on failure.

        Args:
            failed_agent: Agent that failed
            failure_type: Type of failure (code, spec, or both)

        Returns:
            List of agents to restart in order
        """
        to_restart = [failed_agent]

        if failure_type in ["spec", "both"]:
            # Spec changes affect all downstream agents
            affected = DependencyGraph.get_affected_agents(failed_agent)
            to_restart.extend(affected)

        # Get unique and order by dependency
        unique_agents = list(set(to_restart))
        try:
            ordered = DependencyGraph.get_execution_order(unique_agents)
            return ordered
        except ValueError:
            # If can't order, return as-is
            return unique_agents

    @staticmethod
    def analyze_restart_necessity(
        state: AgentState,
        agent_to_restart: str,
        agents_to_check: List[str]
    ) -> Dict[str, bool]:
        """
        Analyze which agents truly need restart.

        Args:
            state: Current state
            agent_to_restart: Agent being restarted
            agents_to_check: Agents to check for restart necessity

        Returns:
            Dict {agent_id: needs_restart}
        """
        results = {}

        for agent in agents_to_check:
            # Check if this agent depends on the restarted agent
            dependencies = DependencyGraph.get_dependencies(agent)

            if agent_to_restart in dependencies:
                results[agent] = True
            else:
                # Check transitive dependencies
                needs_restart = False
                to_check = [agent_to_restart]
                checked = set()

                while to_check and not needs_restart:
                    current = to_check.pop()
                    if current in checked:
                        continue
                    checked.add(current)

                    dependents = DependencyGraph.get_dependents(current)
                    if agent in dependents:
                        needs_restart = True

                    to_check.extend(dependents)

                results[agent] = needs_restart

        return results

    @staticmethod
    def estimate_restart_cost(
        state: AgentState,
        agents_to_restart: List[str]
    ) -> Dict[str, int]:
        """
        Estimate cost (tokens) of restarting agents.

        Args:
            state: Current state
            agents_to_restart: List of agents to restart

        Returns:
            Dict {agent_id: estimated_tokens}
        """
        costs = {}

        for agent in agents_to_restart:
            tokens = DependencyContextLoader.estimate_tokens_for_agent(state, agent)
            costs[agent] = tokens

        return costs
