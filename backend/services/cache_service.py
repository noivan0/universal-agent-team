"""Redis cache service for real-time data management.

Features circuit breaker for Redis failures (Quick Win 4).
"""

import json
import logging
import threading
from typing import Optional, Any, Dict, List
from pathlib import Path
import redis
from datetime import datetime, timedelta, timezone
from functools import wraps
from contextlib import contextmanager
from collections import OrderedDict

from backend.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Circuit Breaker for Redis
# ============================================================================

class CircuitBreakerException(Exception):
    """Base exception for circuit breaker."""
    pass


class CircuitBreakerOpen(CircuitBreakerException):
    """Circuit breaker is open - Redis unavailable."""

    def __init__(self, retry_after_seconds: float = 0):
        self.retry_after_seconds = retry_after_seconds
        if retry_after_seconds > 0:
            super().__init__(
                f"Circuit breaker is open. Retry after {retry_after_seconds:.1f}s"
            )
        else:
            super().__init__("Circuit breaker is open")


class CircuitBreaker:
    """Thread-safe circuit breaker for Redis operations (Quick Win 4)."""

    # State persistence file
    STATE_FILE = Path("/tmp/circuit_breaker_state.json")

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        persist_state: bool = False
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            persist_state: Whether to persist state to disk
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self.persist_state = persist_state

        # Load persisted state if enabled
        if persist_state:
            self._load_state()

    def call(self, func, func_name: str = "", *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            func_name: Name of function (for logging)
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        with self._lock:
            if self.state == "OPEN":
                if self._should_attempt_recovery():
                    self.state = "HALF_OPEN"
                    logger.info(f"Circuit breaker entering HALF_OPEN state for {func_name}")
                else:
                    retry_after = (
                        self.recovery_timeout -
                        (datetime.now() - self.last_failure_time).total_seconds()
                        if self.last_failure_time else 0
                    )
                    logger.error(
                        f"Circuit breaker open for {func_name}. "
                        f"Retry after {retry_after:.1f}s"
                    )
                    raise CircuitBreakerOpen(retry_after)

        try:
            result = func(*args, **kwargs)
            with self._lock:
                self._on_success()
            logger.debug(f"Circuit breaker: success for {func_name}")
            return result

        except redis.ConnectionError as e:
            with self._lock:
                self._on_failure()
            logger.error(f"Redis connection error ({func_name}): {e}")
            raise CircuitBreakerException(f"Redis connection unavailable: {e}") from e

        except redis.TimeoutError as e:
            with self._lock:
                self._on_failure()
            logger.error(f"Redis timeout ({func_name}): {e}")
            raise CircuitBreakerException(f"Redis timeout: {e}") from e

        except Exception as e:
            with self._lock:
                self._on_failure()
            logger.exception(f"Unexpected error in {func_name}: {e}")
            raise CircuitBreakerException(f"Unexpected error: {e}") from e

    def _on_success(self):
        """Handle successful call. Must be called within lock."""
        self.failures = 0
        if self.state != "CLOSED":
            logger.info("Circuit breaker reset to CLOSED")
        self.state = "CLOSED"
        self._save_state()

    def _on_failure(self):
        """Handle failed call. Must be called within lock."""
        self.failures += 1
        self.last_failure_time = datetime.now()
        logger.warning(f"Circuit breaker failure {self.failures}/{self.failure_threshold}")

        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.error("Circuit breaker opened - Redis unavailable")

        self._save_state()

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed for recovery attempt."""
        if not self.last_failure_time:
            return False

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _load_state(self) -> None:
        """Load persisted state from disk.

        Called on initialization if persist_state=True.
        Restores circuit breaker state across process restarts.
        """
        if not self.STATE_FILE.exists():
            return

        try:
            with open(self.STATE_FILE, 'r') as f:
                data = json.load(f)
                self.failures = data.get("failures", 0)
                self.state = data.get("state", "CLOSED")
                last_failure_str = data.get("last_failure_time")
                if last_failure_str:
                    self.last_failure_time = datetime.fromisoformat(last_failure_str)
                logger.info(
                    f"Loaded circuit breaker state: {self.state}, "
                    f"failures={self.failures}"
                )
        except Exception as e:
            logger.error(f"Failed to load circuit breaker state: {e}")

    def _save_state(self) -> None:
        """Persist state to disk.

        Called after state changes if persist_state=True.
        Allows circuit breaker state to survive process restarts.
        """
        if not self.persist_state:
            return

        try:
            with open(self.STATE_FILE, 'w') as f:
                json.dump({
                    "state": self.state,
                    "failures": self.failures,
                    "last_failure_time": (
                        self.last_failure_time.isoformat()
                        if self.last_failure_time else None
                    ),
                }, f)
        except Exception as e:
            logger.error(f"Failed to save circuit breaker state: {e}")


class CacheService:
    """
    Service for managing real-time data in Redis cache.

    Features:
    - Circuit breaker for graceful degradation (Quick Win 4)
    - Thread-safe operations with locks (Quick Win 3)
    - Fallback in-memory cache
    """

    # Fallback cache size limit (class-level constant)
    _MAX_FALLBACK_CACHE_SIZE = 1000

    # Cache key prefixes
    PREFIX_EQUIPMENT = "equipment:"
    PREFIX_CYCLE = "cycle:"
    PREFIX_ALERT = "alert:"
    PREFIX_EQUIPMENT_STATUS = "equipment_status:"

    def __init__(self):
        """Initialize Redis connection with circuit breaker and thread safety."""
        try:
            self.redis_client = redis.from_url(settings.redis.url)
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

        # Initialize circuit breaker with reasonable thresholds
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        # Fallback in-memory cache for when Redis is unavailable
        # Uses OrderedDict to support LRU eviction when max size reached
        self._fallback_cache: OrderedDict = OrderedDict()

        # Thread-safe locks
        self._redis_lock = threading.Lock()  # For Redis operations
        self._cache_lock = threading.RLock()  # Reentrant lock for fallback cache

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False

    def get_circuit_breaker_state(self) -> str:
        """Get current circuit breaker state."""
        return self.circuit_breaker.state

    def _evict_fallback_if_needed(self):
        """Remove oldest entry if fallback cache exceeds max size."""
        if len(self._fallback_cache) >= self._MAX_FALLBACK_CACHE_SIZE:
            oldest_key = next(iter(self._fallback_cache))
            self._fallback_cache.pop(oldest_key)
            logger.debug(f"Evicted oldest fallback cache entry: {oldest_key}")

    def _add_to_fallback_cache(self, key: str, value: Any):
        """Add value to fallback cache with LRU eviction."""
        with self._cache_lock:
            self._fallback_cache[key] = value
            self._evict_fallback_if_needed()
            # Move to end (most recent)
            self._fallback_cache.move_to_end(key)

    @contextmanager
    def batch_operation(self):
        """Context manager for batch operations - acquires all locks at once.

        Use this when performing multiple cache operations that should be atomic.

        Example:
            >>> with cache_service.batch_operation():
            >>>     cache_service.set_equipment_status(1, "running")
            >>>     cache_service.set_equipment_status(2, "idle")
        """
        with self._redis_lock, self._cache_lock:
            yield

    # Equipment Status Management
    def set_equipment_status(self, equipment_id: int, status: str, ttl: int = 3600):
        """
        Set equipment status in cache with thread-safe operations and circuit breaker.

        Args:
            equipment_id: Equipment ID
            status: Status (running, idle, error, maintenance)
            ttl: Time to live in seconds (default 1 hour)
        """
        key = f"{self.PREFIX_EQUIPMENT_STATUS}{equipment_id}"
        data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            if self.redis_client:
                with self._redis_lock:
                    # Use lambda to properly bind arguments for setex(key, ttl, value)
                    self.circuit_breaker.call(
                        lambda: self.redis_client.setex(key, ttl, json.dumps(data)),
                        "setex"
                    )
                logger.debug(f"Set equipment {equipment_id} status to {status}")
            else:
                # No Redis client available, use fallback directly
                self._add_to_fallback_cache(key, data)
        except (CircuitBreakerOpen, CircuitBreakerException):
            logger.warning(f"Circuit breaker open/error, using fallback cache for {key}")
            self._add_to_fallback_cache(key, data)
        except Exception as e:
            logger.error(f"Failed to set equipment status: {e}")
            self._add_to_fallback_cache(key, data)

    def get_equipment_status(self, equipment_id: int) -> Optional[Dict]:
        """
        Get equipment status from cache with fallback and thread-safe operations.

        Uses Redis when available, falls back to memory cache if unavailable.
        Thread-safe with proper locking.
        """
        key = f"{self.PREFIX_EQUIPMENT_STATUS}{equipment_id}"

        try:
            if self.redis_client:
                with self._redis_lock:
                    # Use lambda to properly wrap redis call
                    data = self.circuit_breaker.call(
                        lambda: self.redis_client.get(key),
                        "get"
                    )
                    if data:
                        return json.loads(data)
        except (CircuitBreakerOpen, CircuitBreakerException):
            logger.debug(f"Circuit breaker open/error, using fallback cache for {key}")
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")

        # Return from fallback cache with lock
        with self._cache_lock:
            if key in self._fallback_cache:
                data = self._fallback_cache[key]
                # Move to end (most recent)
                self._fallback_cache.move_to_end(key)
                return data

        return None

    # Real-time Cycle Data
    def cache_active_cycle(self, equipment_id: int, cycle_data: Dict, ttl: int = 3600):
        """
        Cache currently active cycle for an equipment with circuit breaker.

        Args:
            equipment_id: Equipment ID
            cycle_data: Cycle data (start_time, estimated_duration, current_progress)
            ttl: Time to live
        """
        key = f"{self.PREFIX_CYCLE}{equipment_id}:active"

        try:
            if self.redis_client:
                with self._redis_lock:
                    # Use lambda to properly bind setex arguments
                    self.circuit_breaker.call(
                        lambda: self.redis_client.setex(key, ttl, json.dumps(cycle_data)),
                        "setex"
                    )
                logger.debug(f"Cached active cycle for equipment {equipment_id}")
        except (CircuitBreakerOpen, Exception) as e:
            logger.warning(f"Failed to cache cycle, using fallback: {e}")
            self._add_to_fallback_cache(key, cycle_data)

    def get_active_cycle(self, equipment_id: int) -> Optional[Dict]:
        """Get active cycle for equipment with fallback."""
        key = f"{self.PREFIX_CYCLE}{equipment_id}:active"

        try:
            if self.redis_client:
                data = self.circuit_breaker.call(self.redis_client.get, key)
                if data:
                    return json.loads(data)
        except (CircuitBreakerOpen, Exception) as e:
            logger.debug(f"Redis get failed, checking fallback: {e}")

        return self._fallback_cache.get(key)

    def clear_active_cycle(self, equipment_id: int):
        """Clear active cycle when completed."""
        if not self.redis_client:
            return

        key = f"{self.PREFIX_CYCLE}{equipment_id}:active"
        self.redis_client.delete(key)
        logger.debug(f"Cleared active cycle for equipment {equipment_id}")

    # Real-time Cycle History (last N cycles)
    def add_completed_cycle(self, equipment_id: int, cycle_data: Dict):
        """
        Add completed cycle to history.

        Maintains a list of recent cycles for each equipment.
        Keeps last 100 cycles.
        """
        if not self.redis_client:
            return

        key = f"{self.PREFIX_CYCLE}{equipment_id}:history"
        try:
            with self._cache_lock:
                # Add to list (most recent first)
                self.redis_client.lpush(key, json.dumps(cycle_data))
                # Keep only last 100
                self.redis_client.ltrim(key, 0, 99)
                # Set expiry to 24 hours
                self.redis_client.expire(key, 86400)
            logger.debug(f"Added completed cycle to history for equipment {equipment_id}")
        except Exception as e:
            logger.warning(f"Failed to add completed cycle, using fallback: {e}")
            self._add_to_fallback_cache(key, cycle_data)

    def get_cycle_history(self, equipment_id: int, limit: int = 50) -> List[Dict]:
        """Get recent completed cycles."""
        if not self.redis_client:
            return []

        key = f"{self.PREFIX_CYCLE}{equipment_id}:history"
        data = self.redis_client.lrange(key, 0, limit - 1)

        return [json.loads(item) for item in data if item]

    # Real-time Alerts
    def cache_active_alerts(self, equipment_id: int, alerts: List[Dict]):
        """
        Cache active (unacknowledged) alerts for equipment.

        Args:
            equipment_id: Equipment ID
            alerts: List of alert objects
        """
        if not self.redis_client:
            return

        key = f"{self.PREFIX_ALERT}{equipment_id}:active"
        data = {
            "alerts": alerts,
            "count": len(alerts),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        # TTL 30 minutes - will be refreshed on updates
        try:
            with self._redis_lock:
                self.circuit_breaker.call(
                    lambda: self.redis_client.setex(key, 1800, json.dumps(data)),
                    "setex"
                )
            logger.debug(f"Cached {len(alerts)} active alerts for equipment {equipment_id}")
        except Exception as e:
            logger.warning(f"Failed to cache alerts, using fallback: {e}")
            self._add_to_fallback_cache(key, data)

    def get_active_alerts(self, equipment_id: int) -> List[Dict]:
        """Get cached active alerts."""
        if not self.redis_client:
            return []

        key = f"{self.PREFIX_ALERT}{equipment_id}:active"
        data = self.redis_client.get(key)

        if data:
            alert_data = json.loads(data)
            return alert_data.get("alerts", [])
        return []

    # Pub/Sub for Broadcasting Events
    def publish_cycle_completed(self, equipment_id: int, cycle_data: Dict):
        """
        Publish cycle completion event.

        Used for WebSocket broadcasting to connected clients.
        """
        if not self.redis_client:
            return

        channel = "cycles:completed"
        message = {
            "event": "cycle_completed",
            "equipment_id": equipment_id,
            "data": cycle_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.redis_client.publish(channel, json.dumps(message))
        logger.debug(f"Published cycle_completed event for equipment {equipment_id}")

    def publish_alert_created(self, alert_data: Dict):
        """
        Publish new alert event.

        Used for WebSocket broadcasting to connected clients.
        """
        if not self.redis_client:
            return

        channel = "alerts:created"
        message = {
            "event": "alert_created",
            "data": alert_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.redis_client.publish(channel, json.dumps(message))
        logger.debug("Published alert_created event")

    def publish_equipment_status_changed(self, equipment_id: int, status: str):
        """
        Publish equipment status change event.
        """
        if not self.redis_client:
            return

        channel = "equipment:status_changed"
        message = {
            "event": "equipment_status_changed",
            "equipment_id": equipment_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.redis_client.publish(channel, json.dumps(message))
        logger.debug(f"Published status_changed event for equipment {equipment_id}")

    def subscribe(self, channels: List[str]):
        """
        Subscribe to multiple channels.

        Args:
            channels: List of channel names to subscribe to

        Returns:
            Redis PubSub object
        """
        if not self.redis_client:
            return None

        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channels)
        logger.info(f"Subscribed to channels: {channels}")
        return pubsub

    # Cleanup
    def clear_equipment_cache(self, equipment_id: int):
        """Clear all cache for an equipment (when deleted)."""
        if not self.redis_client:
            return

        keys_to_delete = [
            f"{self.PREFIX_EQUIPMENT_STATUS}{equipment_id}",
            f"{self.PREFIX_CYCLE}{equipment_id}:active",
            f"{self.PREFIX_CYCLE}{equipment_id}:history",
            f"{self.PREFIX_ALERT}{equipment_id}:active",
        ]

        for key in keys_to_delete:
            self.redis_client.delete(key)

        logger.info(f"Cleared cache for equipment {equipment_id}")


# Global cache service instance
cache_service = CacheService()
