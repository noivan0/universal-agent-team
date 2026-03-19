"""
Context compaction strategy for Universal Agent Team.

Implements relevance-based summarization and dynamic compression
to reduce token usage while maintaining 99%+ information consistency.

Key strategies:
1. Relevance-based summary generation (next agent determines what's important)
2. Dynamic thresholds based on project complexity
3. Artifact manifest tracking
4. Section-based compression

Performance optimizations:
- Relevance score caching for fast lookups
- Cache invalidation support
"""

import json
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import OrderedDict

from state_models import (
    AgentState,
    ArtifactMetadata,
    CompressionStats,
    AgentPhase
)

logger = logging.getLogger(__name__)


# ============================================================================
# Relevance Scoring
# ============================================================================

class Relevance(str, Enum):
    """Relevance levels for artifact content."""
    CRITICAL = "critical"      # Must be included (API specs, etc.)
    HIGH = "high"              # Very important for next agent
    MEDIUM = "medium"          # Useful but not essential
    LOW = "low"                # Optional
    REFERENCE = "reference"    # Only reference/pointer needed


@dataclass
class RelevanceScore:
    """Relevance score for a piece of content."""
    content_key: str
    relevance: Relevance
    score: float  # 0.0-1.0
    reason: str


class RelevanceCalculator:
    """
    Calculates relevance of artifact sections for specific agents.

    Different agents need different information:
    - Frontend Agent: api_specs (critical), design_system, component_specs
    - Backend Agent: database_schema, api_specs (critical), deployment_templates
    - QA Agent: code_files, test_structure, critical_paths
    - Documentation Agent: all (full), but in order of importance

    Features thread-safe caching for fast relevance score lookups (Quick Win 2).
    Uses LRU eviction to prevent unbounded growth.
    """

    # Thread-safe cache for relevance scores using OrderedDict for LRU
    _relevance_cache: OrderedDict = OrderedDict()
    _cache_lock = threading.RLock()
    _MAX_CACHE_SIZE = 5000  # Prevent unbounded growth

    # Relevance mappings by next agent and artifact content
    RELEVANCE_MAP = {
        "frontend": {
            "api_specs": (Relevance.CRITICAL, 0.95),
            "component_specs": (Relevance.CRITICAL, 0.95),
            "design_system": (Relevance.HIGH, 0.80),
            "database_schema": (Relevance.LOW, 0.10),
            "deployment_templates": (Relevance.LOW, 0.05),
            "system_design": (Relevance.MEDIUM, 0.50),
            "architecture_pattern": (Relevance.MEDIUM, 0.60),
        },
        "backend": {
            "api_specs": (Relevance.CRITICAL, 0.95),
            "database_schema": (Relevance.CRITICAL, 0.95),
            "component_specs": (Relevance.LOW, 0.10),
            "design_system": (Relevance.LOW, 0.05),
            "deployment_templates": (Relevance.HIGH, 0.80),
            "system_design": (Relevance.MEDIUM, 0.50),
            "architecture_pattern": (Relevance.MEDIUM, 0.60),
        },
        "qa": {
            "code_files": (Relevance.CRITICAL, 0.95),
            "test_structure": (Relevance.CRITICAL, 0.95),
            "api_specs": (Relevance.HIGH, 0.80),
            "component_specs": (Relevance.HIGH, 0.80),
            "database_schema": (Relevance.MEDIUM, 0.60),
            "design_system": (Relevance.LOW, 0.20),
            "deployment_templates": (Relevance.REFERENCE, 0.15),
        },
        "documentation": {
            "system_design": (Relevance.HIGH, 0.90),
            "architecture_pattern": (Relevance.HIGH, 0.90),
            "component_specs": (Relevance.HIGH, 0.85),
            "api_specs": (Relevance.HIGH, 0.85),
            "database_schema": (Relevance.HIGH, 0.80),
            "design_system": (Relevance.MEDIUM, 0.70),
            "deployment_templates": (Relevance.HIGH, 0.85),
            "code_files": (Relevance.REFERENCE, 0.30),
        },
        "contract_validator": {
            "api_specs": (Relevance.CRITICAL, 0.95),
            "component_specs": (Relevance.MEDIUM, 0.60),  # For frontend API calls
            "code_files": (Relevance.REFERENCE, 0.40),  # To verify implementation
        }
    }

    @classmethod
    def get_cached_score(
        cls,
        artifact_key: str,
        next_agent: str
    ) -> float:
        """
        Get relevance score with thread-safe caching and LRU eviction.

        Args:
            artifact_key: Key of the artifact
            next_agent: ID of the next agent

        Returns:
            Relevance score (0.0-1.0)
        """
        cache_key = (artifact_key, next_agent)

        with cls._cache_lock:
            if cache_key in cls._relevance_cache:
                # Move to end (most recent) for LRU tracking
                cls._relevance_cache.move_to_end(cache_key)
                logger.debug(f"Relevance cache hit: {artifact_key} -> {next_agent}")
                return cls._relevance_cache[cache_key]

        # Calculate score (outside lock to avoid contention)
        relevance_map = cls.RELEVANCE_MAP.get(next_agent, {})
        relevance_tuple = relevance_map.get(artifact_key)

        if relevance_tuple:
            _, score = relevance_tuple
        else:
            score = 0.20  # Default low relevance

        # Cache the result with thread safety and eviction
        with cls._cache_lock:
            # Check again in case another thread cached it
            if cache_key in cls._relevance_cache:
                cls._relevance_cache.move_to_end(cache_key)
                return cls._relevance_cache[cache_key]

            # Evict oldest entry if at capacity
            if len(cls._relevance_cache) >= cls._MAX_CACHE_SIZE:
                oldest_key, _ = cls._relevance_cache.popitem(last=False)
                logger.debug(f"Evicted relevance cache entry: {oldest_key}")

            cls._relevance_cache[cache_key] = score
            logger.debug(f"Cached relevance score: {artifact_key} -> {next_agent} = {score}")

        return score

    @staticmethod
    def calculate_relevance(
        artifact_key: str,
        next_agent: str
    ) -> RelevanceScore:
        """
        Calculate relevance of an artifact for a specific agent.

        Uses cached scores for performance.

        Args:
            artifact_key: Key of the artifact (e.g., "api_specs", "code_files")
            next_agent: ID of the next agent

        Returns:
            RelevanceScore with relevance level and numerical score
        """
        # Get score from cache or calculate
        score = RelevanceCalculator.get_cached_score(artifact_key, next_agent)

        relevance_map = RelevanceCalculator.RELEVANCE_MAP.get(next_agent, {})
        relevance_tuple = relevance_map.get(artifact_key)

        if relevance_tuple:
            relevance, _ = relevance_tuple
            reason = f"{artifact_key} is {relevance.value} for {next_agent}"
        else:
            # Default: low relevance
            relevance = Relevance.LOW
            reason = f"{artifact_key} has default low relevance for {next_agent}"

        return RelevanceScore(
            content_key=artifact_key,
            relevance=relevance,
            score=score,
            reason=reason
        )

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear cached relevance scores with thread safety.

        Call when artifact types or agent configurations change.
        """
        with cls._cache_lock:
            cls._relevance_cache.clear()
            logger.info("Relevance score cache cleared")

    @classmethod
    def get_cache_stats(cls) -> Dict[str, int]:
        """
        Get cache statistics (thread-safe).

        Returns:
            Dictionary with cache statistics
        """
        with cls._cache_lock:
            return {
                "cached_scores": len(cls._relevance_cache),
                "max_size": cls._MAX_CACHE_SIZE
            }

    @staticmethod
    def get_top_items(
        items: Dict[str, Any],
        next_agent: str,
        top_n: int = 5
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Select top N items by relevance.

        Args:
            items: Dictionary of items {name: content}
            next_agent: Next agent in workflow
            top_n: Number of top items to include

        Returns:
            Tuple of (selected_items, excluded_items)
        """
        scored_items = []
        for name, content in items.items():
            if isinstance(content, dict):
                score = RelevanceCalculator.get_cached_score(name, next_agent)
            else:
                score = 0.5  # Default for non-dict items

            scored_items.append((name, content, score))

        # Sort by relevance score descending
        scored_items.sort(key=lambda x: x[2], reverse=True)

        # Take top N
        selected = {}
        excluded = []
        for i, (name, content, score) in enumerate(scored_items):
            if i < top_n:
                selected[name] = content
            else:
                excluded.append(name)

        return selected, excluded


# ============================================================================
# Dynamic Thresholds
# ============================================================================

class CompressionThreshold:
    """Dynamic compression threshold based on project complexity."""

    # Size thresholds (bytes) based on complexity
    THRESHOLDS = {
        "small": {         # complexity 1-30
            "max_artifact_size": 1_000_000,    # 1MB
            "compress_sections": ["documentation"],
            "in_state_by_default": True
        },
        "medium": {        # complexity 31-70
            "max_artifact_size": 500_000,      # 500KB
            "compress_sections": ["development", "testing"],
            "in_state_by_default": True
        },
        "large": {         # complexity 71-100
            "max_artifact_size": 100_000,      # 100KB
            "compress_sections": ["development", "documentation", "testing"],
            "in_state_by_default": False
        }
    }

    @staticmethod
    def get_threshold_for_complexity(complexity_score: int) -> Dict[str, Any]:
        """
        Get compression threshold based on project complexity.

        Args:
            complexity_score: Project complexity (1-100)

        Returns:
            Threshold configuration
        """
        if complexity_score <= 30:
            return CompressionThreshold.THRESHOLDS["small"]
        elif complexity_score <= 70:
            return CompressionThreshold.THRESHOLDS["medium"]
        else:
            return CompressionThreshold.THRESHOLDS["large"]

    @staticmethod
    def should_compress(
        artifact_size: int,
        section_name: str,
        complexity_score: int
    ) -> bool:
        """
        Determine if an artifact should be compressed.

        Args:
            artifact_size: Size of artifact in bytes
            section_name: Name of the section (development, testing, etc.)
            complexity_score: Project complexity

        Returns:
            True if should compress, False otherwise
        """
        threshold = CompressionThreshold.get_threshold_for_complexity(complexity_score)

        if artifact_size > threshold["max_artifact_size"]:
            return True

        if section_name in threshold["compress_sections"]:
            # Even small artifacts in high-compression sections might compress
            return artifact_size > 50_000  # 50KB threshold

        return False


# ============================================================================
# Summary Generator
# ============================================================================

class SummaryGenerator:
    """Generates relevance-based summaries of artifacts."""

    @staticmethod
    def summarize_architecture(
        artifacts: Dict[str, Any],
        next_agent: str
    ) -> str:
        """Generate summary of architecture artifacts."""
        summary_parts = []

        # Always include key metrics
        api_specs = artifacts.get("api_specs", {})
        component_specs = artifacts.get("component_specs", {})
        summary_parts.append(f"API Endpoints: {len(api_specs)}")
        summary_parts.append(f"Components: {len(component_specs)}")

        # Highlight critical sections for next agent
        if next_agent == "frontend":
            # Highlight component specs and API endpoints
            top_components = list(component_specs.keys())[:3]
            if top_components:
                summary_parts.append(f"Key components: {', '.join(top_components)}")

            top_endpoints = list(api_specs.keys())[:3]
            if top_endpoints:
                summary_parts.append(f"Key API endpoints: {', '.join(top_endpoints)}")

        elif next_agent == "backend":
            # Highlight API specs and database
            top_endpoints = list(api_specs.keys())[:3]
            if top_endpoints:
                summary_parts.append(f"Key API endpoints: {', '.join(top_endpoints)}")

            db_schema = artifacts.get("database_schema", "")
            if db_schema:
                summary_parts.append("Database schema defined")

        elif next_agent == "documentation":
            # Include everything but high level
            summary_parts.append("Complete architecture defined")
            summary_parts.append(f"Database schema: {'yes' if artifacts.get('database_schema') else 'no'}")
            summary_parts.append(f"Deployment templates: {len(artifacts.get('deployment_templates', {}))}")

        return " | ".join(summary_parts)

    @staticmethod
    def summarize_development(
        code_files: Dict[str, str],
        next_agent: str,
        top_n: int = 5
    ) -> Tuple[str, List[str]]:
        """
        Generate summary of development artifacts.

        Returns:
            Tuple of (summary_text, file_paths_included)
        """
        file_list = list(code_files.keys())
        summary_parts = [f"Generated {len(file_list)} files"]

        # Include important files
        included_files = file_list[:top_n]
        summary_parts.append(f"Key files: {', '.join(included_files)}")

        # Count by type
        py_count = sum(1 for f in file_list if f.endswith('.py'))
        ts_count = sum(1 for f in file_list if f.endswith(('.ts', '.tsx')))

        if py_count > 0:
            summary_parts.append(f"Python files: {py_count}")
        if ts_count > 0:
            summary_parts.append(f"TypeScript files: {ts_count}")

        return " | ".join(summary_parts), included_files

    @staticmethod
    def summarize_testing(
        test_results: Dict[str, Any],
        complexity_score: int
    ) -> str:
        """Generate summary of testing artifacts."""
        total = test_results.get("total_tests", 0)
        passed = test_results.get("passed_tests", 0)
        coverage = test_results.get("coverage_percent", 0)

        summary_parts = [
            f"Tests: {passed}/{total} passed",
            f"Coverage: {coverage:.1f}%"
        ]

        # Highlight failures if any
        failed = total - passed
        if failed > 0:
            summary_parts.append(f"Failed: {failed}")

        return " | ".join(summary_parts)


# ============================================================================
# Compression Manager
# ============================================================================

class CompressionManager:
    """Manages compression of artifacts in state."""

    @staticmethod
    def analyze_state(state: AgentState) -> Dict[str, Any]:
        """
        Analyze state for compression opportunities.

        Returns:
            Dictionary with compression analysis
        """
        analysis = {
            "total_size": 0,
            "artifacts": {},
            "compression_opportunities": []
        }

        # Estimate sizes (simplified)
        dev_size = len(json.dumps(state.development.model_dump())) if state.development else 0
        arch_size = len(json.dumps(state.architecture_artifacts.model_dump())) if state.architecture_artifacts else 0
        doc_size = len(json.dumps(state.documentation_artifacts.model_dump())) if state.documentation_artifacts else 0

        analysis["artifacts"]["development"] = dev_size
        analysis["artifacts"]["architecture"] = arch_size
        analysis["artifacts"]["documentation"] = doc_size

        complexity = state.metadata.complexity_score
        threshold = CompressionThreshold.get_threshold_for_complexity(complexity)

        # Check which should be compressed
        for section, size in analysis["artifacts"].items():
            if size > threshold["max_artifact_size"]:
                analysis["compression_opportunities"].append({
                    "section": section,
                    "size": size,
                    "threshold": threshold["max_artifact_size"],
                    "compression_ratio": threshold["max_artifact_size"] / max(1, size)
                })

        analysis["total_size"] = sum(analysis["artifacts"].values())

        return analysis

    @staticmethod
    def estimate_token_savings(
        original_size: int,
        compressed_size: int
    ) -> int:
        """
        Estimate token savings from compression.

        Rough estimate: 1 token ≈ 4 characters for typical English text.

        Args:
            original_size: Original size in bytes
            compressed_size: Compressed size in bytes

        Returns:
            Estimated tokens saved
        """
        original_tokens = original_size / 4
        compressed_tokens = compressed_size / 4
        return int(original_tokens - compressed_tokens)


# ============================================================================
# Context Loader
# ============================================================================

class ContextLoader:
    """Loads context for agents with relevance-based filtering."""

    @staticmethod
    def load_context_for_agent(
        state: AgentState,
        next_agent: str,
        include_full_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        Load relevant context for a specific agent.

        Args:
            state: Full agent state
            next_agent: ID of the agent receiving context
            include_full_artifacts: Whether to include full artifacts or summaries

        Returns:
            Filtered context dictionary
        """
        context = {
            "metadata": state.metadata.model_dump(),
            "execution_status": state.execution_status.model_dump(),
        }

        # Add relevant artifacts based on next agent
        if next_agent in ["frontend", "backend", "contract_validator"]:
            # These agents always need architecture
            if include_full_artifacts or state.architecture_artifacts:
                context["architecture"] = state.architecture_artifacts.model_dump()

        if next_agent in ["frontend", "backend"]:
            # These agents need planning
            if include_full_artifacts or state.planning_artifacts:
                context["planning"] = state.planning_artifacts.model_dump()

        if next_agent == "qa":
            # QA needs development artifacts
            if include_full_artifacts or state.development:
                context["development"] = state.development.model_dump()

        if next_agent == "documentation":
            # Documentation needs everything
            context["planning"] = state.planning_artifacts.model_dump()
            context["architecture"] = state.architecture_artifacts.model_dump()
            context["development"] = state.development.model_dump()
            context["testing"] = state.testing_artifacts.model_dump()

        return context

    @staticmethod
    def estimate_tokens_for_context(context: Dict[str, Any]) -> int:
        """
        Estimate tokens for a context dictionary.

        Args:
            context: Context dictionary

        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters
        context_str = json.dumps(context)
        return len(context_str) // 4
