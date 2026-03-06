"""Custom exception classes for the Cycle Time Monitoring System."""

from typing import Optional, List, Any


class CycleMonitorException(Exception):
    """Base exception for all application-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None
    ):
        """
        Initialize exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details
            }
        }


class ValidationError(CycleMonitorException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Any] = None
    ):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            details: Additional validation details
        """
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field, "details": details} if field else details
        )


class NotFoundError(CycleMonitorException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: Any):
        """
        Initialize not found error.

        Args:
            resource_type: Type of resource (e.g., 'Equipment')
            resource_id: ID of the missing resource
        """
        super().__init__(
            message=f"{resource_type} with ID {resource_id} not found",
            error_code="NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class DuplicateError(CycleMonitorException):
    """Raised when trying to create a duplicate resource."""

    def __init__(self, resource_type: str, field: str, value: str):
        """
        Initialize duplicate error.

        Args:
            resource_type: Type of resource (e.g., 'Equipment')
            field: Field that has duplicate value
            value: The duplicate value
        """
        super().__init__(
            message=f"{resource_type} with {field}='{value}' already exists",
            error_code="DUPLICATE_RESOURCE",
            status_code=409,
            details={"resource_type": resource_type, "field": field, "value": value}
        )


class InvalidConfigurationError(CycleMonitorException):
    """Raised when cycle configuration is invalid."""

    def __init__(self, message: str, details: Optional[dict] = None):
        """
        Initialize invalid configuration error.

        Args:
            message: Error message
            details: Configuration details that are invalid
        """
        super().__init__(
            message=message,
            error_code="INVALID_CONFIG",
            status_code=422,
            details=details
        )


class ThresholdValidationError(InvalidConfigurationError):
    """Raised when cycle time thresholds are invalid."""

    def __init__(
        self,
        min_time: float,
        max_time: float,
        target_time: Optional[float] = None
    ):
        """
        Initialize threshold validation error.

        Args:
            min_time: Minimum cycle time
            max_time: Maximum cycle time
            target_time: Target cycle time (if provided)
        """
        issues: List[str] = []

        if min_time > max_time:
            issues.append(f"min_cycle_time ({min_time}) must be <= max_cycle_time ({max_time})")

        if target_time is not None:
            if target_time < min_time or target_time > max_time:
                issues.append(
                    f"target_cycle_time ({target_time}) must be between "
                    f"min_cycle_time ({min_time}) and max_cycle_time ({max_time})"
                )

        if min_time <= 0:
            issues.append("min_cycle_time must be greater than 0")

        if max_time <= 0:
            issues.append("max_cycle_time must be greater than 0")

        message = "; ".join(issues) if issues else "Invalid cycle time thresholds"

        super().__init__(
            message=message,
            details={
                "min_cycle_time": min_time,
                "max_cycle_time": max_time,
                "target_cycle_time": target_time,
                "issues": issues
            }
        )


class DatabaseError(CycleMonitorException):
    """Raised when a database operation fails."""

    def __init__(self, operation: str, message: str):
        """
        Initialize database error.

        Args:
            operation: The database operation that failed (e.g., 'INSERT', 'SELECT')
            message: Error message from the database
        """
        super().__init__(
            message=f"Database error during {operation}: {message}",
            error_code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation, "database_message": message}
        )


class CycleDetectionError(CycleMonitorException):
    """Raised when cycle detection fails."""

    def __init__(self, equipment_id: int, message: str, details: Optional[dict] = None):
        """
        Initialize cycle detection error.

        Args:
            equipment_id: ID of the equipment
            message: Error message
            details: Additional details about the detection failure
        """
        super().__init__(
            message=f"Cycle detection failed for equipment {equipment_id}: {message}",
            error_code="CYCLE_DETECTION_ERROR",
            status_code=422,
            details={"equipment_id": equipment_id, **details} if details else {"equipment_id": equipment_id}
        )


class InsufficientDataError(CycleDetectionError):
    """Raised when there is insufficient data for cycle detection."""

    def __init__(self, equipment_id: int, data_points: int, minimum_required: int):
        """
        Initialize insufficient data error.

        Args:
            equipment_id: ID of the equipment
            data_points: Number of data points provided
            minimum_required: Minimum number of data points required
        """
        super().__init__(
            equipment_id=equipment_id,
            message=f"Insufficient data for cycle detection ({data_points} points, need {minimum_required})",
            details={
                "data_points": data_points,
                "minimum_required": minimum_required
            }
        )


class AuthenticationError(CycleMonitorException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        """
        Initialize authentication error.

        Args:
            message: Error message
        """
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            status_code=401
        )


class AuthorizationError(CycleMonitorException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        """
        Initialize authorization error.

        Args:
            message: Error message
        """
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_FAILED",
            status_code=403
        )


class ExternalServiceError(CycleMonitorException):
    """Raised when an external service call fails."""

    def __init__(self, service_name: str, message: str):
        """
        Initialize external service error.

        Args:
            service_name: Name of the external service
            message: Error message
        """
        super().__init__(
            message=f"External service error ({service_name}): {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service_name": service_name}
        )


class TimeoutError(CycleMonitorException):
    """Raised when an operation times out."""

    def __init__(self, operation: str, timeout_seconds: float):
        """
        Initialize timeout error.

        Args:
            operation: The operation that timed out
            timeout_seconds: The timeout value in seconds
        """
        super().__init__(
            message=f"Operation '{operation}' timed out after {timeout_seconds} seconds",
            error_code="OPERATION_TIMEOUT",
            status_code=504,
            details={"operation": operation, "timeout_seconds": timeout_seconds}
        )


class ConflictError(CycleMonitorException):
    """Raised when there is a conflict with current state."""

    def __init__(self, resource_type: str, message: str, details: Optional[dict] = None):
        """
        Initialize conflict error.

        Args:
            resource_type: Type of resource
            message: Error message
            details: Additional details
        """
        super().__init__(
            message=f"{resource_type} conflict: {message}",
            error_code="RESOURCE_CONFLICT",
            status_code=409,
            details=details
        )


class RateLimitError(CycleMonitorException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60):
        """
        Initialize rate limit error.

        Args:
            retry_after: Number of seconds to wait before retrying
        """
        super().__init__(
            message=f"Rate limit exceeded. Please retry after {retry_after} seconds",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after}
        )
