"""
Error catalog with standardized messages and guidance.

Provides consistent, helpful error messages across the API with
actionable guidance for resolution.

Example:
    from backend.core.error_catalog import ErrorCatalog, get_error

    # Get structured error information
    error = get_error("CACHE_UNAVAILABLE")
    # Returns:
    # {
    #     "error_code": "CACHE_UNAVAILABLE",
    #     "message": "Cache service temporarily unavailable",
    #     "guidance": "Data will be served from database with slight delay",
    #     "status_code": 503
    # }

    # Use in exception handler
    raise HTTPException(
        status_code=error["status_code"],
        detail=error
    )
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ErrorCatalog:
    """Centralized error message catalog with guidance."""

    ERRORS: Dict[str, Dict[str, Any]] = {
        # Infrastructure Errors
        "CACHE_UNAVAILABLE": {
            "message": "Cache service temporarily unavailable",
            "guidance": "Data will be served from database with slight delay",
            "status_code": 503,
            "category": "infrastructure",
        },
        "DATABASE_CONNECTION_FAILED": {
            "message": "Cannot connect to database",
            "guidance": "Check database server is running and connection string is valid",
            "docs": "https://docs.example.com/troubleshooting/database",
            "status_code": 503,
            "category": "infrastructure",
        },
        "CONFIGURATION_INVALID": {
            "message": "Configuration validation failed",
            "guidance": "Check environment variables match required format. See .env.example",
            "docs": "https://docs.example.com/configuration",
            "status_code": 500,
            "category": "configuration",
        },

        # Resource Errors
        "EQUIPMENT_NOT_FOUND": {
            "message": "Equipment not found: {equipment_id}",
            "guidance": "Create equipment first or verify the equipment ID",
            "status_code": 404,
            "category": "resource",
        },
        "PROJECT_NOT_FOUND": {
            "message": "Project not found: {project_id}",
            "guidance": "Create project first using /api/projects or use existing project ID",
            "status_code": 404,
            "category": "resource",
        },
        "AGENT_NOT_FOUND": {
            "message": "Agent not found: {agent_id}",
            "guidance": "Agent ID may be incorrect or agent may have been deleted",
            "status_code": 404,
            "category": "resource",
        },

        # Validation Errors
        "INVALID_REQUEST": {
            "message": "Invalid request parameters",
            "guidance": "Check request body matches API schema. Use /api/docs for details",
            "status_code": 400,
            "category": "validation",
        },
        "MISSING_REQUIRED_FIELD": {
            "message": "Missing required field: {field}",
            "guidance": "Provide {field} in request body",
            "status_code": 400,
            "category": "validation",
        },
        "INVALID_COMPLEXITY_SCORE": {
            "message": "Complexity score must be between 1 and 100, got {score}",
            "guidance": "Use a complexity score from 1 (simple) to 100 (very complex)",
            "status_code": 400,
            "category": "validation",
        },

        # State Errors
        "INVALID_STATE": {
            "message": "Invalid workflow state",
            "guidance": "Workflow may be in unexpected state. Check workflow history in logs",
            "status_code": 400,
            "category": "state",
        },
        "STATE_CORRUPTION": {
            "message": "Workflow state is corrupted",
            "guidance": "Restart workflow from last checkpoint or manually reset state",
            "status_code": 500,
            "category": "state",
        },
        "CHECKPOINT_NOT_FOUND": {
            "message": "Checkpoint not found: {checkpoint_id}",
            "guidance": "Checkpoint may have been cleaned up. Start workflow fresh",
            "status_code": 404,
            "category": "state",
        },

        # Agent Errors
        "AGENT_EXECUTION_FAILED": {
            "message": "Agent execution failed: {agent_id}",
            "guidance": "Check agent logs for details. Agent will retry automatically",
            "status_code": 500,
            "category": "agent",
        },
        "AGENT_TIMEOUT": {
            "message": "Agent execution timeout after {timeout_seconds}s",
            "guidance": "Request was too complex or agent is overloaded. Try simpler request",
            "status_code": 504,
            "category": "agent",
        },
        "MAX_RETRIES_EXCEEDED": {
            "message": "Max retries exceeded for {agent_id}",
            "guidance": "Agent failed after multiple attempts. Check error logs for root cause",
            "status_code": 500,
            "category": "agent",
        },

        # API Errors
        "METHOD_NOT_ALLOWED": {
            "message": "HTTP method not allowed for this endpoint",
            "guidance": "Check HTTP method (GET, POST, etc.) matches API documentation",
            "status_code": 405,
            "category": "api",
        },
        "REQUEST_TIMEOUT": {
            "message": "Request took too long to complete",
            "guidance": "Request timeout is {timeout_seconds}s. Try with smaller input",
            "status_code": 504,
            "category": "api",
        },

        # Authentication/Authorization
        "UNAUTHORIZED": {
            "message": "Unauthorized",
            "guidance": "Provide valid authentication credentials",
            "status_code": 401,
            "category": "auth",
        },
        "FORBIDDEN": {
            "message": "Access denied",
            "guidance": "You don't have permission to access this resource",
            "status_code": 403,
            "category": "auth",
        },

        # Business Logic Errors
        "DUPLICATE_EQUIPMENT": {
            "message": "Equipment with name '{name}' already exists",
            "guidance": "Use different name or update existing equipment",
            "status_code": 400,
            "category": "business",
        },
        "INVALID_EQUIPMENT_STATE": {
            "message": "Equipment is in invalid state for this operation",
            "guidance": "Equipment may need to be stopped or restarted first",
            "status_code": 400,
            "category": "business",
        },
    }

    @staticmethod
    def get_error(
        error_code: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get error details with optional formatting.

        Args:
            error_code: Error code from catalog
            **kwargs: Arguments to format error message

        Returns:
            Dictionary with error details

        Raises:
            ValueError: If error_code not found in catalog
        """
        if error_code not in ErrorCatalog.ERRORS:
            logger.warning(f"Unknown error code: {error_code}")
            return {
                "error_code": error_code,
                "message": "Unknown error",
                "guidance": "Check logs for details",
                "status_code": 500,
                "category": "unknown",
            }

        error = dict(ErrorCatalog.ERRORS[error_code])  # Copy to avoid mutation

        # Format message with kwargs
        message = error.pop("message", "")
        try:
            message = message.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format argument for {error_code}: {e}")

        # Format guidance with kwargs
        guidance = error.pop("guidance", "")
        try:
            guidance = guidance.format(**kwargs)
        except KeyError:
            pass  # Optional fields can fail gracefully

        return {
            "error_code": error_code,
            "message": message,
            "guidance": guidance,
            **error,  # Include remaining fields (status_code, docs, category)
        }

    @staticmethod
    def has_error(error_code: str) -> bool:
        """Check if error code exists in catalog."""
        return error_code in ErrorCatalog.ERRORS

    @staticmethod
    def list_errors_by_category(category: str) -> Dict[str, Dict[str, Any]]:
        """Get all errors in a category."""
        return {
            code: details
            for code, details in ErrorCatalog.ERRORS.items()
            if details.get("category") == category
        }


def get_error(error_code: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to get error details.

    Args:
        error_code: Error code from catalog
        **kwargs: Arguments to format error message

    Returns:
        Dictionary with error details
    """
    return ErrorCatalog.get_error(error_code, **kwargs)


def create_http_exception(error_code: str, **kwargs):
    """
    Create HTTPException from error catalog.

    Example:
        raise create_http_exception("EQUIPMENT_NOT_FOUND", equipment_id=123)

    Args:
        error_code: Error code from catalog
        **kwargs: Arguments to format error message

    Returns:
        HTTPException ready to raise
    """
    from fastapi import HTTPException

    error = get_error(error_code, **kwargs)
    return HTTPException(
        status_code=error.pop("status_code", 500),
        detail=error,
    )
