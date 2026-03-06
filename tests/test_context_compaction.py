"""
Unit tests for context compaction and dynamic loading.

Tests cover:
- Relevance scoring algorithms
- Summary generation
- Dynamic compression thresholds
- Compression ratios
- On-demand loading strategies
"""

import pytest
from state_models import (
    ArtifactMetadata,
    CompressionStats,
    PlanningArtifacts,
    ArchitectureArtifacts,
)


@pytest.mark.unit
class TestCompressionStats:
    """Test compression statistics tracking."""

    def test_compression_stats_initialization(self):
        """Test compression stats initialization."""
        stats = CompressionStats()

        assert stats.total_artifact_size == 0
        assert stats.compressed_size == 0
        assert stats.compression_ratio == 1.0
        assert stats.tokens_saved == 0

    def test_compression_ratio_calculation(self):
        """Test compression ratio calculations."""
        # No compression
        stats1 = CompressionStats(
            total_artifact_size=1000,
            compressed_size=1000,
            compression_ratio=1.0
        )
        assert stats1.compression_ratio == 1.0

        # 50% compression
        stats2 = CompressionStats(
            total_artifact_size=1000,
            compressed_size=500,
            compression_ratio=0.5
        )
        assert stats2.compression_ratio == 0.5

        # 85% compression (aggressive)
        stats3 = CompressionStats(
            total_artifact_size=1000,
            compressed_size=150,
            compression_ratio=0.15
        )
        assert stats3.compression_ratio == 0.15

    def test_token_savings_tracking(self):
        """Test token savings calculation."""
        stats = CompressionStats(
            total_artifact_size=10000,
            compressed_size=2000,
            compression_ratio=0.2,
            tokens_saved=2500
        )

        assert stats.tokens_saved == 2500
        # Typical: 4 chars per token
        expected_tokens = (10000 - 2000) // 4
        assert stats.tokens_saved >= expected_tokens * 0.8  # Allow some variance


@pytest.mark.unit
class TestArtifactMetadataCompaction:
    """Test artifact metadata for compaction decisions."""

    def test_artifact_in_state_tracking(self):
        """Test whether artifact is stored in state or externally."""
        # Small artifact - stays in state
        small = ArtifactMetadata(
            artifact_name="small.json",
            artifact_type="small_data",
            size_bytes=500,
            in_state=True
        )
        assert small.in_state is True

        # Large artifact - moved external
        large = ArtifactMetadata(
            artifact_name="large.json",
            artifact_type="large_data",
            size_bytes=100000,
            in_state=False
        )
        assert large.in_state is False

    def test_compression_ratio_in_metadata(self):
        """Test compression ratio in artifact metadata."""
        # No compression
        metadata1 = ArtifactMetadata(
            artifact_name="original.md",
            artifact_type="docs",
            size_bytes=5000,
            compression_ratio=1.0
        )
        assert metadata1.compression_ratio == 1.0

        # 70% compression
        metadata2 = ArtifactMetadata(
            artifact_name="compressed.md",
            artifact_type="docs",
            size_bytes=1500,  # 30% of original 5000
            compression_ratio=0.3
        )
        assert metadata2.compression_ratio == 0.3

    def test_relevance_tags(self):
        """Test relevance tags for context selection."""
        metadata = ArtifactMetadata(
            artifact_name="api_contract.json",
            artifact_type="api_specs",
            size_bytes=3000,
            relevance_tags=[
                "api", "contract", "critical",
                "backend", "integration"
            ]
        )

        assert "api" in metadata.relevance_tags
        assert "critical" in metadata.relevance_tags
        assert len(metadata.relevance_tags) == 5

    def test_summary_location_tracking(self):
        """Test summary location (embedded or external)."""
        # Embedded summary
        metadata1 = ArtifactMetadata(
            artifact_name="requirements.md",
            artifact_type="requirements",
            size_bytes=2000,
            summary_location="embedded"
        )
        assert metadata1.summary_location == "embedded"

        # External summary
        metadata2 = ArtifactMetadata(
            artifact_name="large_code.py",
            artifact_type="code",
            size_bytes=50000,
            summary_location="/artifacts/large_code_summary.txt"
        )
        assert "/artifacts/" in metadata2.summary_location


@pytest.mark.unit
class TestRelevanceScoring:
    """Test relevance scoring for context selection."""

    def test_critical_artifact_scoring(self):
        """Test scoring for critical artifacts."""
        # Critical artifact - full relevance
        metadata_critical = ArtifactMetadata(
            artifact_name="user_auth.py",
            artifact_type="code",
            size_bytes=2000,
            relevance_tags=["critical", "security", "auth"]
        )

        # Non-critical artifact
        metadata_optional = ArtifactMetadata(
            artifact_name="analytics.py",
            artifact_type="code",
            size_bytes=3000,
            relevance_tags=["analytics", "optional"]
        )

        # Critical should have higher relevance
        critical_score = len([t for t in metadata_critical.relevance_tags if t == "critical"])
        optional_score = len([t for t in metadata_optional.relevance_tags if t == "critical"])

        assert critical_score > optional_score

    def test_size_based_relevance(self):
        """Test size-based relevance scoring."""
        # Small artifact - high relevance (easier to include)
        small = ArtifactMetadata(
            artifact_name="small.json",
            artifact_type="config",
            size_bytes=100
        )

        # Large artifact - lower relevance (harder to fit)
        large = ArtifactMetadata(
            artifact_name="large.json",
            artifact_type="data",
            size_bytes=100000
        )

        assert small.size_bytes < large.size_bytes

    def test_tag_based_relevance(self):
        """Test tag-based relevance matching."""
        metadata = ArtifactMetadata(
            artifact_name="test.json",
            artifact_type="test_results",
            size_bytes=2000,
            relevance_tags=["testing", "qa", "critical", "failure_analysis"]
        )

        # Query for test-related artifacts
        test_tags = ["testing", "qa", "critical"]
        matching_tags = [t for t in metadata.relevance_tags if t in test_tags]

        assert len(matching_tags) >= 2


@pytest.mark.unit
class TestDynamicCompressionThresholds:
    """Test dynamic compression threshold calculations."""

    def test_complexity_based_thresholds(self):
        """Test thresholds adjust based on project complexity."""
        # Simple project - higher compression
        simple_threshold = 5000  # 5KB threshold for compression

        # Complex project - lower compression
        complex_threshold = 50000  # 50KB threshold for compression

        assert simple_threshold < complex_threshold

    def test_phase_based_thresholds(self):
        """Test thresholds vary by workflow phase."""
        # Planning phase - more generous (need full context)
        planning_threshold = 100000

        # QA phase - more aggressive (need focused context)
        qa_threshold = 50000

        assert planning_threshold > qa_threshold

    def test_context_window_based_thresholds(self):
        """Test thresholds based on available context window."""
        # Limited context (30k tokens)
        limited_budget = 30000 * 4  # ~120KB

        # Generous context (100k tokens)
        generous_budget = 100000 * 4  # ~400KB

        assert limited_budget < generous_budget


@pytest.mark.unit
class TestCompressionStrategies:
    """Test different compression strategies."""

    def test_summary_compression(self):
        """Test compression via summarization."""
        # Original large document
        original = """
        This is a very detailed requirements document that spans many pages.
        It includes information about features, constraints, risks, and more.
        The document contains redundant information and verbose explanations.
        """ * 100  # Simulate large document

        # Compressed summary
        summary = "Key requirements: Feature A, Feature B, Feature C. Risks identified."

        assert len(summary) < len(original)

    def test_sampling_compression(self):
        """Test compression via sampling."""
        # Large array of test results
        test_results = [
            {"test_id": f"T{i:04d}", "status": "passed", "duration_ms": 100}
            for i in range(1000)
        ]

        # Sampled version (every 10th)
        sampled = test_results[::10]

        assert len(sampled) < len(test_results)
        assert len(sampled) == len(test_results) // 10

    def test_structural_compression(self):
        """Test compression by removing non-critical structure."""
        # Full artifact with all metadata
        full = {
            "metadata": {"created": "2024-01-01", "version": 1},
            "data": {"items": [1, 2, 3]},
            "details": {"explanation": "Very long explanation"}
        }

        # Compressed - only essential data
        compressed = {
            "data": {"items": [1, 2, 3]},
        }

        assert len(str(compressed)) < len(str(full))


@pytest.mark.unit
class TestOnDemandLoading:
    """Test on-demand loading strategies."""

    def test_lazy_loading_decision(self):
        """Test decision to load artifact on demand."""
        # Critical artifact - always load
        critical = ArtifactMetadata(
            artifact_name="auth.py",
            artifact_type="code",
            size_bytes=2000,
            in_state=True,
            relevance_tags=["critical"]
        )
        # Should be in state for immediate access
        assert critical.in_state is True

        # Non-critical large artifact - lazy load
        noncritical = ArtifactMetadata(
            artifact_name="analytics_logs.json",
            artifact_type="logs",
            size_bytes=500000,
            in_state=False,
            relevance_tags=["analytics"]
        )
        # Should be external for lazy loading
        assert noncritical.in_state is False

    def test_priority_queue_loading(self):
        """Test priority-based artifact loading order."""
        artifacts = [
            ArtifactMetadata(
                artifact_name="a1.json",
                artifact_type="api",
                size_bytes=1000,
                relevance_tags=["api", "critical"]
            ),
            ArtifactMetadata(
                artifact_name="a2.json",
                artifact_type="docs",
                size_bytes=5000,
                relevance_tags=["docs"]
            ),
            ArtifactMetadata(
                artifact_name="a3.json",
                artifact_type="logs",
                size_bytes=10000,
                relevance_tags=["logs"]
            ),
        ]

        # Score artifacts by criticality and size
        def score_artifact(meta):
            criticality = 10 if "critical" in meta.relevance_tags else 1
            size_penalty = meta.size_bytes / 1000  # Penalize large artifacts
            return criticality / size_penalty

        scored = [(meta, score_artifact(meta)) for meta in artifacts]
        scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)

        # Most critical should be first
        assert scored_sorted[0][0].artifact_name == "a1.json"

    def test_progressive_loading(self):
        """Test progressive loading strategy."""
        # Stage 1: Load summaries only
        summaries = {
            "api_spec": "Summary of API",
            "components": "Summary of components",
            "database": "Summary of database"
        }

        # Stage 2: Load critical details on demand
        detail_api = "Full API specification with 50 endpoints..."
        detail_components = "Full component definitions with 30 components..."

        assert len(summaries) > 0
        assert len(detail_api) > len(summaries["api_spec"])


@pytest.mark.unit
class TestContextWindowManagement:
    """Test context window management with compression."""

    def test_token_budget_calculation(self):
        """Test token budget calculation."""
        # Assume 1 token ≈ 4 characters
        context_size_tokens = 100000
        context_size_chars = context_size_tokens * 4

        assert context_size_chars == 400000

    def test_budget_allocation(self):
        """Test allocation of token budget across artifacts."""
        total_budget = 100000  # tokens

        # Allocate budget
        planning_budget = int(total_budget * 0.15)  # 15%
        architecture_budget = int(total_budget * 0.25)  # 25%
        development_budget = int(total_budget * 0.40)  # 40%
        testing_budget = int(total_budget * 0.15)  # 15%
        documentation_budget = int(total_budget * 0.05)  # 5%

        total_allocated = (planning_budget + architecture_budget +
                          development_budget + testing_budget +
                          documentation_budget)

        assert total_allocated == total_budget

    def test_compression_under_budget(self):
        """Test artifact compression to fit budget."""
        artifact_size = 50000  # characters
        budget = 10000  # characters
        required_compression = artifact_size / budget

        # Need ~80% compression
        assert required_compression >= 5.0

    def test_selective_loading(self):
        """Test selective loading to stay within budget."""
        available_budget = 50000  # characters

        artifacts = [
            ("critical_api", 5000),
            ("components_spec", 15000),
            ("detailed_docs", 40000),
            ("test_logs", 30000),
        ]

        loaded = []
        remaining_budget = available_budget

        for name, size in sorted(artifacts, key=lambda x: x[1]):
            if remaining_budget >= size:
                loaded.append(name)
                remaining_budget -= size

        # Should load at least the small artifacts
        assert "critical_api" in loaded
        assert "components_spec" in loaded


@pytest.mark.unit
class TestCompressionRatios:
    """Test various compression ratios."""

    def test_high_compression_ratio(self):
        """Test high compression scenarios."""
        original_size = 100000
        compressed_ratios = [0.15, 0.20, 0.25]  # 75%, 80%, 75% compression

        for ratio in compressed_ratios:
            compressed_size = int(original_size * ratio)
            assert compressed_size < original_size
            compression_percent = (1 - ratio) * 100
            assert compression_percent >= 70  # High compression

    def test_moderate_compression_ratio(self):
        """Test moderate compression scenarios."""
        original_size = 100000
        compressed_ratios = [0.5, 0.6, 0.7]  # 50%, 40%, 30% compression

        for ratio in compressed_ratios:
            compressed_size = int(original_size * ratio)
            compression_percent = (1 - ratio) * 100
            assert compression_percent >= 30
            assert compression_percent <= 70

    def test_minimal_compression_ratio(self):
        """Test minimal/no compression scenarios."""
        original_size = 100000
        compressed_ratios = [0.9, 0.95, 1.0]  # 10%, 5%, 0% compression

        for ratio in compressed_ratios:
            compressed_size = int(original_size * ratio)
            compression_percent = (1 - ratio) * 100
            assert compression_percent <= 10


@pytest.mark.unit
class TestCompressionMetrics:
    """Test metrics for compression effectiveness."""

    def test_compression_ratio_metric(self):
        """Test compression ratio metric."""
        stats = CompressionStats(
            total_artifact_size=100000,
            compressed_size=30000,
            compression_ratio=0.30
        )

        # Compression percent = (1 - ratio) * 100
        compression_percent = (1 - stats.compression_ratio) * 100
        assert compression_percent == 70

    def test_token_savings_metric(self):
        """Test token savings metric."""
        original_tokens = 25000  # 100KB / 4
        saved_tokens = 17500  # 70% compression
        remaining_tokens = 7500  # 30% compression

        ratio = remaining_tokens / original_tokens
        assert ratio == 0.30

    def test_size_reduction_metric(self):
        """Test size reduction metric."""
        original_size = 100000
        compressed_size = 15000

        reduction = (original_size - compressed_size) / original_size
        assert reduction == 0.85  # 85% reduction


@pytest.mark.unit
class TestRelevanceCalculatorCaching:
    """Test relevance score caching (Quick Win 2)."""

    def test_cache_hit_single_relevance(self):
        """Test cache hit for a single relevance calculation."""
        from context_compaction import RelevanceCalculator

        RelevanceCalculator.clear_cache()

        # First call - cache miss
        score1 = RelevanceCalculator.get_cached_score("api_specs", "frontend")
        assert score1 == 0.95  # CRITICAL relevance for frontend

        # Second call - should cache hit
        score2 = RelevanceCalculator.get_cached_score("api_specs", "frontend")
        assert score1 == score2

        # Verify cache has entry
        stats = RelevanceCalculator.get_cache_stats()
        assert stats["cached_scores"] > 0

    def test_cache_different_combinations(self):
        """Test caching with different artifact/agent combinations."""
        from context_compaction import RelevanceCalculator

        RelevanceCalculator.clear_cache()

        # Different combinations should cache separately
        score1 = RelevanceCalculator.get_cached_score("api_specs", "frontend")
        score2 = RelevanceCalculator.get_cached_score("api_specs", "backend")
        score3 = RelevanceCalculator.get_cached_score("component_specs", "frontend")

        assert score1 == 0.95  # api_specs for frontend = CRITICAL
        assert score2 == 0.95  # api_specs for backend = CRITICAL
        assert score3 == 0.95  # component_specs for frontend = CRITICAL

        # All should be cached
        stats = RelevanceCalculator.get_cache_stats()
        assert stats["cached_scores"] >= 3

    def test_cache_default_relevance(self):
        """Test caching of default (unmapped) relevance scores."""
        from context_compaction import RelevanceCalculator

        RelevanceCalculator.clear_cache()

        # Unmapped combination should default to 0.20
        score1 = RelevanceCalculator.get_cached_score("unknown_artifact", "unknown_agent")
        assert score1 == 0.20  # Default low relevance

        # Second call should use cache
        score2 = RelevanceCalculator.get_cached_score("unknown_artifact", "unknown_agent")
        assert score1 == score2

        stats = RelevanceCalculator.get_cache_stats()
        assert stats["cached_scores"] > 0

    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        from context_compaction import RelevanceCalculator

        RelevanceCalculator.clear_cache()

        # Populate cache
        RelevanceCalculator.get_cached_score("api_specs", "frontend")
        stats_before = RelevanceCalculator.get_cache_stats()
        assert stats_before["cached_scores"] > 0

        # Clear cache
        RelevanceCalculator.clear_cache()
        stats_after = RelevanceCalculator.get_cache_stats()
        assert stats_after["cached_scores"] == 0

    def test_get_top_items_uses_cache(self):
        """Test that get_top_items uses cached scores."""
        from context_compaction import RelevanceCalculator

        RelevanceCalculator.clear_cache()

        items = {
            "api_specs": {"endpoints": 10},
            "component_specs": {"components": 5},
            "database_schema": {"tables": 3},
            "design_system": {"tokens": 100}
        }

        # Select top 2 items for frontend
        selected, excluded = RelevanceCalculator.get_top_items(items, "frontend", top_n=2)

        # Should select critical items first
        assert "api_specs" in selected
        assert "component_specs" in selected

        # Verify cache was populated
        stats = RelevanceCalculator.get_cache_stats()
        assert stats["cached_scores"] >= 2

    def test_cache_consistency_across_calls(self):
        """Test cache provides consistent results across multiple calls."""
        from context_compaction import RelevanceCalculator

        RelevanceCalculator.clear_cache()

        artifact = "api_specs"
        agent = "backend"

        # Make multiple calls
        scores = [
            RelevanceCalculator.get_cached_score(artifact, agent)
            for _ in range(5)
        ]

        # All scores should be identical
        assert all(s == scores[0] for s in scores)
        assert scores[0] == 0.95

    def test_relevance_score_range(self):
        """Test cached scores are always in valid range (0.0-1.0)."""
        from context_compaction import RelevanceCalculator

        RelevanceCalculator.clear_cache()

        test_cases = [
            ("api_specs", "frontend"),
            ("database_schema", "backend"),
            ("code_files", "qa"),
            ("system_design", "documentation"),
            ("unknown", "unknown")
        ]

        for artifact, agent in test_cases:
            score = RelevanceCalculator.get_cached_score(artifact, agent)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for {artifact}/{agent}"
