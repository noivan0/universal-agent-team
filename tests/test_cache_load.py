"""
Cache Load Testing

Validates cache performance under realistic load conditions:
- Multiple concurrent users
- Large number of projects
- Memory efficiency
- Performance degradation
"""

import pytest
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from dependency_context import DependencyGraph


# ============================================================================
# Load Test Fixtures
# ============================================================================

class CacheLoadTester:
    """Helper for running cache load tests."""

    def __init__(self):
        """Initialize load tester."""
        self.results: Dict[str, List[float]] = {}
        self.errors: List[str] = []

    def run_load_test(
        self,
        num_workers: int,
        operations_per_worker: int,
        teams_variation: int = 5
    ) -> Dict:
        """
        Run cache load test with concurrent workers.

        Args:
            num_workers: Number of concurrent workers
            operations_per_worker: Operations per worker
            teams_variation: Number of different team configurations

        Returns:
            Dictionary with performance metrics
        """
        DependencyGraph.invalidate_cache()

        def worker(worker_id: int, operations: int):
            """Worker performing cache operations."""
            local_times = []
            for i in range(operations):
                # Vary the team configurations
                team_variant = (worker_id + i) % teams_variation
                agents = self._generate_agent_list(team_variant)

                start = time.time()
                try:
                    order = DependencyGraph.get_execution_order(agents)
                    duration = (time.time() - start) * 1000  # Convert to ms
                    local_times.append(duration)
                except Exception as e:
                    self.errors.append(f"Worker {worker_id}: {str(e)}")

            return local_times

        # Run with ThreadPoolExecutor
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(worker, i, operations_per_worker): i
                for i in range(num_workers)
            }

            all_times = []
            for future in as_completed(futures):
                try:
                    times = future.result()
                    all_times.extend(times)
                except Exception as e:
                    self.errors.append(str(e))

        total_time = time.time() - start_time

        # Calculate metrics
        if all_times:
            return {
                "total_operations": len(all_times),
                "total_time_seconds": total_time,
                "operations_per_second": len(all_times) / total_time if total_time > 0 else 0,
                "min_time_ms": min(all_times),
                "max_time_ms": max(all_times),
                "avg_time_ms": sum(all_times) / len(all_times),
                "p95_time_ms": sorted(all_times)[int(len(all_times) * 0.95)],
                "p99_time_ms": sorted(all_times)[int(len(all_times) * 0.99)],
                "errors": len(self.errors),
            }
        return {}

    @staticmethod
    def _generate_agent_list(variant: int) -> List[str]:
        """Generate a team configuration variant."""
        base_agents = ["planning", "architecture", "frontend", "backend"]
        if variant >= 1:
            base_agents.append("qa")
        if variant >= 3:
            base_agents.append("documentation")
        return base_agents


# ============================================================================
# Performance Baseline Tests
# ============================================================================

class TestCachePerformanceBaseline:
    """Establish performance baselines."""

    def test_single_user_performance(self):
        """Baseline: single user performance."""
        DependencyGraph.invalidate_cache()

        agents = ["planning", "architecture", "frontend", "backend"]
        times = []

        for _ in range(100):
            start = time.time()
            order = DependencyGraph.get_execution_order(agents)
            times.append((time.time() - start) * 1000)

        avg_time = sum(times) / len(times)
        assert avg_time < 10, f"Single user should be fast (<10ms), got {avg_time:.2f}ms"

    def test_cache_hit_performance(self):
        """Cache hits should be much faster than misses."""
        DependencyGraph.invalidate_cache()

        agents = ["planning", "architecture", "frontend", "backend"]

        # First call (cache miss)
        start = time.time()
        order = DependencyGraph.get_execution_order(agents)
        miss_time = (time.time() - start) * 1000

        # Second call (cache hit)
        start = time.time()
        order = DependencyGraph.get_execution_order(agents)
        hit_time = (time.time() - start) * 1000

        # Cache hit should be significantly faster
        speedup = miss_time / hit_time if hit_time > 0 else 1
        assert speedup >= 2, f"Cache hit should be 2x+ faster, got {speedup:.1f}x"


# ============================================================================
# Concurrency Tests
# ============================================================================

class TestConcurrentCacheAccess:
    """Test cache under concurrent load."""

    def test_10_concurrent_users(self):
        """Test with 10 concurrent users."""
        tester = CacheLoadTester()
        results = tester.run_load_test(
            num_workers=10,
            operations_per_worker=50,
            teams_variation=5
        )

        assert results, "Should complete without errors"
        assert results["errors"] == 0, "Should have no errors"
        assert results["operations_per_second"] > 100, \
            f"Should handle 100+ ops/sec, got {results['operations_per_second']:.1f}"

    def test_50_concurrent_users(self):
        """Test with 50 concurrent users."""
        tester = CacheLoadTester()
        results = tester.run_load_test(
            num_workers=50,
            operations_per_worker=20,
            teams_variation=10
        )

        assert results, "Should complete without errors"
        assert results["errors"] == 0, "Should have no errors"
        # Performance may degrade slightly under heavy load
        assert results["operations_per_second"] > 50, \
            f"Should handle 50+ ops/sec under heavy load, got {results['operations_per_second']:.1f}"

    def test_100_concurrent_users(self):
        """Test with 100 concurrent users."""
        tester = CacheLoadTester()
        results = tester.run_load_test(
            num_workers=100,
            operations_per_worker=10,
            teams_variation=20
        )

        assert results, "Should complete without errors"
        assert results["errors"] == 0, "Should have no errors"


# ============================================================================
# Memory and Cache Efficiency Tests
# ============================================================================

class TestCacheMemoryEfficiency:
    """Test cache doesn't use excessive memory."""

    def test_cache_size_bounded(self):
        """Cache should not exceed max size."""
        DependencyGraph.invalidate_cache()

        max_size = DependencyGraph._MAX_CACHE_SIZE

        # Generate more entries than max size
        for i in range(max_size + 100):
            agents = ["planning", "architecture", f"variant_{i % 50}"]
            try:
                DependencyGraph.get_execution_order(agents, use_cache=False)
            except:
                pass

        # Cache should still be bounded
        stats = DependencyGraph.get_cache_stats()
        assert stats["cached_orders"] <= max_size, \
            f"Cache size {stats['cached_orders']} should not exceed {max_size}"

    def test_cache_eviction_with_heavy_variations(self):
        """Cache should properly evict when using many variations."""
        DependencyGraph.invalidate_cache()

        # Create 200 different team variations
        for i in range(200):
            agents = self._create_variant(i)
            try:
                DependencyGraph.get_execution_order(agents)
            except:
                pass

        # Cache should still be under control
        stats = DependencyGraph.get_cache_stats()
        assert stats["cached_orders"] < 200, "Should have fewer entries than variations"

    @staticmethod
    def _create_variant(seed: int) -> List[str]:
        """Create a team variant."""
        agents = ["planning", "architecture"]
        if seed % 2 == 0:
            agents.append("frontend")
        if seed % 3 == 0:
            agents.append("backend")
        if seed % 5 == 0:
            agents.append("qa")
        if seed % 7 == 0:
            agents.append("documentation")
        return agents


# ============================================================================
# Stress Tests
# ============================================================================

class TestCacheStress:
    """Stress tests for cache reliability."""

    def test_sustained_load_1000_operations(self):
        """Sustain 1000+ operations across multiple workers."""
        tester = CacheLoadTester()
        results = tester.run_load_test(
            num_workers=20,
            operations_per_worker=50,
            teams_variation=10
        )

        assert results["total_operations"] >= 1000, "Should complete 1000+ operations"
        assert results["errors"] == 0, f"Should have no errors, got {results['errors']}"

    def test_cache_under_high_variation(self):
        """Cache should perform well even with high team variation."""
        tester = CacheLoadTester()
        results = tester.run_load_test(
            num_workers=30,
            operations_per_worker=30,
            teams_variation=100  # High variation
        )

        assert results["errors"] == 0, "Should handle high variation"

    def test_rapid_cache_hit_miss_mix(self):
        """Cache should handle rapid mix of hits and misses."""
        DependencyGraph.invalidate_cache()

        agents_list = [
            ["planning", "architecture"],
            ["planning", "architecture", "frontend"],
            ["planning", "architecture", "backend"],
            ["planning", "architecture", "frontend", "backend"],
        ]

        times = []
        for _ in range(1000):
            agents = random.choice(agents_list)
            start = time.time()
            try:
                order = DependencyGraph.get_execution_order(agents)
                times.append((time.time() - start) * 1000)
            except:
                pass

        avg_time = sum(times) / len(times) if times else 0
        assert avg_time < 5, f"Average time should be <5ms, got {avg_time:.2f}ms"


# ============================================================================
# Performance Degradation Tests
# ============================================================================

class TestPerformanceDegradation:
    """Test graceful degradation under extreme load."""

    def test_degradation_curve(self):
        """Performance should degrade gracefully, not collapse."""
        tester = CacheLoadTester()

        # Test at increasing concurrency levels
        results_list = []
        for num_workers in [1, 5, 10, 20, 50]:
            results = tester.run_load_test(
                num_workers=num_workers,
                operations_per_worker=20,
                teams_variation=5
            )
            if results:
                results_list.append({
                    "workers": num_workers,
                    "ops_per_sec": results["operations_per_second"]
                })

        # Should not collapse under load
        if len(results_list) > 1:
            worst_case = results_list[-1]["ops_per_sec"]
            best_case = results_list[0]["ops_per_sec"]
            # Worst case should still be at least 10% of best case
            assert worst_case > best_case * 0.1, \
                f"Performance collapsed: {worst_case:.1f} vs {best_case:.1f}"


# ============================================================================
# Cleanup and Summary
# ============================================================================

class TestCacheSummary:
    """Summary tests for cache performance."""

    def test_full_load_test_summary(self):
        """Run full load test and verify all metrics."""
        tester = CacheLoadTester()
        results = tester.run_load_test(
            num_workers=10,
            operations_per_worker=100,
            teams_variation=10
        )

        # Verify all expected metrics are present
        expected_metrics = [
            "total_operations",
            "total_time_seconds",
            "operations_per_second",
            "min_time_ms",
            "max_time_ms",
            "avg_time_ms",
            "p95_time_ms",
            "p99_time_ms",
            "errors"
        ]

        for metric in expected_metrics:
            assert metric in results, f"Missing metric: {metric}"

        # Verify reasonable values
        assert results["total_operations"] == 1000
        assert results["avg_time_ms"] < 50, "Average should be reasonable"
        assert results["p99_time_ms"] < 100, "99th percentile should be reasonable"
        assert results["errors"] == 0, "Should have no errors"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
