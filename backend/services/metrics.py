"""
Metrics collection and observability module.

Provides comprehensive metrics for system monitoring:
- Cache performance (hits, misses, evictions)
- Request timing and performance
- Error tracking and aggregation
- Resource utilization
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# Metrics Data Models
# ============================================================================

@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 100

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate (0.0 to 1.0)."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": f"{self.hit_rate * 100:.1f}%",
            "evictions": self.evictions,
            "size": f"{self.size}/{self.max_size}",
            "total_requests": self.hits + self.misses,
        }


@dataclass
class RequestMetrics:
    """Metrics for API request performance."""
    endpoint: str
    count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    error_count: int = 0

    @property
    def average_duration_ms(self) -> float:
        """Calculate average request duration."""
        return self.total_duration_ms / self.count if self.count > 0 else 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "endpoint": self.endpoint,
            "count": self.count,
            "average_duration_ms": f"{self.average_duration_ms:.2f}",
            "min_duration_ms": f"{self.min_duration_ms:.2f}",
            "max_duration_ms": f"{self.max_duration_ms:.2f}",
            "error_count": self.error_count,
            "error_rate_percent": f"{(self.error_count / self.count * 100) if self.count > 0 else 0:.1f}%",
        }


# ============================================================================
# Metrics Collector
# ============================================================================

class MetricsCollector:
    """
    Centralized metrics collection and reporting.

    Features:
    - Thread-safe metrics collection
    - Cache hit/miss tracking
    - Request performance tracking
    - Error aggregation
    - Periodic persistence to disk
    """

    def __init__(self, storage_dir: str = "/tmp"):
        """
        Initialize metrics collector.

        Args:
            storage_dir: Directory for storing metrics snapshots
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Core metrics
        self.cache_metrics = CacheMetrics()
        self.request_metrics: Dict[str, RequestMetrics] = {}
        self.error_counts: Dict[str, int] = {}
        self.start_time = datetime.now()

        # Thread safety
        self._lock = threading.RLock()

    # ========== Cache Metrics ==========

    def record_cache_hit(self, size: int = 0, max_size: int = 100) -> None:
        """Record cache hit."""
        with self._lock:
            self.cache_metrics.hits += 1
            if size > 0:
                self.cache_metrics.size = size
            if max_size > 0:
                self.cache_metrics.max_size = max_size

    def record_cache_miss(self, size: int = 0, max_size: int = 100) -> None:
        """Record cache miss."""
        with self._lock:
            self.cache_metrics.misses += 1
            if size > 0:
                self.cache_metrics.size = size
            if max_size > 0:
                self.cache_metrics.max_size = max_size

    def record_cache_eviction(self) -> None:
        """Record cache eviction."""
        with self._lock:
            self.cache_metrics.evictions += 1

    # ========== Request Metrics ==========

    def record_request(
        self,
        endpoint: str,
        duration_ms: float,
        error: bool = False
    ) -> None:
        """
        Record API request metrics.

        Args:
            endpoint: API endpoint path
            duration_ms: Request duration in milliseconds
            error: Whether request resulted in error
        """
        with self._lock:
            if endpoint not in self.request_metrics:
                self.request_metrics[endpoint] = RequestMetrics(endpoint=endpoint)

            metrics = self.request_metrics[endpoint]
            metrics.count += 1
            metrics.total_duration_ms += duration_ms
            metrics.min_duration_ms = min(metrics.min_duration_ms, duration_ms)
            metrics.max_duration_ms = max(metrics.max_duration_ms, duration_ms)

            if error:
                metrics.error_count += 1

    # ========== Error Metrics ==========

    def record_error(self, error_type: str) -> None:
        """
        Record error occurrence.

        Args:
            error_type: Type of error (exception class name or custom type)
        """
        with self._lock:
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    # ========== Summary & Reporting ==========

    def get_summary(self) -> Dict:
        """
        Get comprehensive metrics summary.

        Returns:
            Dictionary with all metrics
        """
        with self._lock:
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()

            request_summaries = {}
            for endpoint, metrics in self.request_metrics.items():
                request_summaries[endpoint] = metrics.to_dict()

            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": f"{uptime_seconds:.1f}",
                "cache": self.cache_metrics.to_dict(),
                "requests": {
                    "endpoints": request_summaries,
                    "total_requests": sum(m.count for m in self.request_metrics.values()),
                },
                "errors": {
                    "error_types": self.error_counts.copy(),
                    "total_errors": sum(self.error_counts.values()),
                },
            }

    def save_snapshot(self, name: Optional[str] = None) -> Path:
        """
        Save metrics snapshot to disk.

        Args:
            name: Custom name for snapshot (default: timestamp)

        Returns:
            Path to saved snapshot file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = name or f"metrics_{timestamp}.json"
        file_path = self.storage_dir / filename

        try:
            with open(file_path, 'w') as f:
                json.dump(self.get_summary(), f, indent=2)
            logger.info(f"Saved metrics snapshot: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save metrics snapshot: {e}")
            return file_path

    def get_cache_hit_rate(self) -> float:
        """Get current cache hit rate (0.0 to 1.0)."""
        return self.cache_metrics.hit_rate

    def get_request_count(self, endpoint: Optional[str] = None) -> int:
        """Get request count for specific endpoint or all endpoints."""
        with self._lock:
            if endpoint:
                return self.request_metrics.get(endpoint, RequestMetrics(endpoint=endpoint)).count
            return sum(m.count for m in self.request_metrics.values())

    def get_error_count(self, error_type: Optional[str] = None) -> int:
        """Get error count for specific type or total."""
        with self._lock:
            if error_type:
                return self.error_counts.get(error_type, 0)
            return sum(self.error_counts.values())

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self.cache_metrics = CacheMetrics()
            self.request_metrics.clear()
            self.error_counts.clear()
            self.start_time = datetime.now()
            logger.info("Metrics reset")


# ============================================================================
# Global Metrics Instance
# ============================================================================

# Global metrics collector
metrics_collector = MetricsCollector()


# ============================================================================
# Metrics Context Managers
# ============================================================================

class MetricsContext:
    """Context manager for recording metrics with timing."""

    def __init__(self, endpoint: str):
        """
        Initialize metrics context.

        Args:
            endpoint: API endpoint to record metrics for
        """
        self.endpoint = endpoint
        self.start_time: Optional[datetime] = None

    def __enter__(self):
        """Start timing."""
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record metrics and end timing."""
        if self.start_time:
            duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
            error = exc_type is not None

            metrics_collector.record_request(self.endpoint, duration_ms, error=error)

            if error:
                logger.warning(
                    f"Request to {self.endpoint} failed after {duration_ms:.2f}ms: {exc_type.__name__}"
                )
