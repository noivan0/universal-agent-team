"""
Health check endpoints for infrastructure monitoring.

Provides:
- /health - Liveness probe (is server running?)
- /ready - Readiness probe (is server ready for traffic?)
- /metrics - Health metrics for monitoring

These endpoints are essential for Kubernetes probes and load balancer
health checks.

Example:
    # Kubernetes liveness probe
    livenessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 10

    # Kubernetes readiness probe
    readinessProbe:
      httpGet:
        path: /ready
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["infrastructure"])

# Track application start time
_app_start_time = time.time()


class HealthChecker:
    """Performs health checks for various components."""

    @staticmethod
    def check_database(db: Session) -> bool:
        """Check database connectivity."""
        try:
            db.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @staticmethod
    def check_memory() -> Dict[str, Any]:
        """Check memory usage."""
        import psutil

        try:
            memory = psutil.virtual_memory()
            return {
                "available": memory.available,
                "percent": memory.percent,
                "ok": memory.percent < 90,  # Alert if > 90%
            }
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {"available": 0, "percent": 0, "ok": False}

    @staticmethod
    def check_disk() -> Dict[str, Any]:
        """Check disk usage."""
        import psutil

        try:
            disk = psutil.disk_usage("/")
            return {
                "available": disk.free,
                "percent": disk.percent,
                "ok": disk.percent < 90,  # Alert if > 90%
            }
        except Exception as e:
            logger.error(f"Disk check failed: {e}")
            return {"available": 0, "percent": 0, "ok": False}


# ============================================================================
# Health Check Endpoints
# ============================================================================


@router.get(
    "/health",
    tags=["Infrastructure"],
    summary="Liveness probe",
    description="Check if server is running. Used by load balancers and K8s.",
)
async def health_check(db: Session = next(get_db())) -> Dict[str, Any]:
    """
    Liveness probe endpoint.

    Returns 200 if server is running, 503 if unhealthy.

    Returns:
        Health status with component checks
    """
    checks = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": time.time() - _app_start_time,
        "components": {
            "database": HealthChecker.check_database(db),
            "memory": HealthChecker.check_memory(),
            "disk": HealthChecker.check_disk(),
        },
    }

    # Overall status is unhealthy if any critical component fails
    all_ok = (
        checks["components"]["database"]
        and checks["components"]["memory"]["ok"]
        and checks["components"]["disk"]["ok"]
    )

    if not all_ok:
        checks["status"] = "degraded"
        raise HTTPException(
            status_code=503,
            detail=checks,
        )

    return checks


@router.get(
    "/ready",
    tags=["Infrastructure"],
    summary="Readiness probe",
    description="Check if server is ready to accept traffic. Used by K8s.",
)
async def readiness_check(db: Session = next(get_db())) -> Dict[str, Any]:
    """
    Readiness probe endpoint.

    Returns 200 if server is ready, 503 if not ready.
    Used by Kubernetes to determine if pod should receive traffic.

    Returns:
        Readiness status
    """
    # Check if database is accessible
    if not HealthChecker.check_database(db):
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "reason": "Database not accessible",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # Check if memory/disk is critically low
    memory = HealthChecker.check_memory()
    disk = HealthChecker.check_disk()

    if not memory["ok"] or not disk["ok"]:
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "reason": "Resource constraints (memory/disk)",
                "memory_percent": memory["percent"],
                "disk_percent": disk["percent"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    return {
        "ready": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": time.time() - _app_start_time,
    }


@router.get(
    "/metrics",
    tags=["Infrastructure"],
    summary="Health metrics",
    description="Detailed health metrics for monitoring systems.",
)
async def metrics(db: Session = next(get_db())) -> Dict[str, Any]:
    """
    Detailed health metrics endpoint.

    Returns comprehensive metrics for monitoring dashboards.

    Returns:
        Detailed health and performance metrics
    """
    uptime = time.time() - _app_start_time

    db_ok = HealthChecker.check_database(db)
    memory = HealthChecker.check_memory()
    disk = HealthChecker.check_disk()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime,
        "server": {
            "status": "running",
        },
        "database": {
            "healthy": db_ok,
            "status": "connected" if db_ok else "disconnected",
        },
        "resources": {
            "memory": {
                "percent_used": memory["percent"],
                "bytes_available": memory["available"],
                "healthy": memory["ok"],
            },
            "disk": {
                "percent_used": disk["percent"],
                "bytes_available": disk["available"],
                "healthy": disk["ok"],
            },
        },
        "overall_status": (
            "healthy"
            if db_ok and memory["ok"] and disk["ok"]
            else "degraded"
        ),
    }


# ============================================================================
# Startup/Shutdown Hooks
# ============================================================================


def setup_health_checks(app) -> None:
    """
    Setup health check endpoints on FastAPI app.

    Called during app initialization.

    Args:
        app: FastAPI application instance
    """
    app.include_router(router)
    logger.info("Health check endpoints configured")
