"""OpenAPI documentation and schema definitions.

This module provides enhanced OpenAPI documentation for the Cycle Time
Monitoring System API, including:

- Detailed endpoint descriptions with examples
- Request/response schema documentation
- Error handling documentation
- Integration examples
- Best practices

The OpenAPI specification is auto-generated from this module and available at:
- /api/docs (Swagger UI)
- /api/redoc (ReDoc)
- /api/openapi.json (Raw OpenAPI specification)
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class APIDocumentation:
    """Container for API documentation definitions."""

    # ========================================================================
    # Equipment Endpoints Documentation
    # ========================================================================

    EQUIPMENT_GET = {
        "summary": "List all equipment",
        "description": """
        Retrieve a paginated list of all monitored equipment.

        This endpoint returns basic equipment information including:
        - Equipment ID and name
        - Equipment type and location
        - Current status and cycle configuration
        - Last activity timestamp

        ### Performance:
        - Pagination default: 50 items per page
        - Response time: ~50-100ms
        - Database query: Uses indexed lookups

        ### Example:
        ```bash
        curl -X GET "http://localhost:8000/api/equipments?skip=0&limit=50"
        ```

        ### Response:
        ```json
        [
          {
            "id": 1,
            "name": "Assembly Line A",
            "equipment_type": "assembly",
            "location": "Factory Floor 1",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z"
          }
        ]
        ```
        """,
        "tags": ["Equipments"],
        "responses": {
            "200": {
                "description": "List of equipment",
                "content": {
                    "application/json": {
                        "example": [
                            {
                                "id": 1,
                                "name": "Assembly Line A",
                                "equipment_type": "assembly",
                                "location": "Factory Floor 1",
                                "status": "active",
                                "created_at": "2024-01-01T00:00:00Z",
                            }
                        ]
                    }
                },
            }
        },
    }

    EQUIPMENT_CREATE = {
        "summary": "Create new equipment",
        "description": """
        Create a new equipment record in the monitoring system.

        ### Required Fields:
        - `name`: Unique equipment identifier (string)
        - `equipment_type`: Type of equipment (assembly, testing, packaging, etc.)

        ### Optional Fields:
        - `location`: Physical location in facility
        - `description`: Equipment notes and metadata

        ### Validation:
        - Equipment name must be unique (returns 409 Conflict if duplicate)
        - Equipment type must be valid (from predefined list)

        ### Example:
        ```bash
        curl -X POST "http://localhost:8000/api/equipments" \\
          -H "Content-Type: application/json" \\
          -d '{
            "name": "Assembly Line B",
            "equipment_type": "assembly",
            "location": "Factory Floor 2",
            "description": "New high-speed assembly line"
          }'
        ```

        ### Response:
        ```json
        {
          "id": 2,
          "name": "Assembly Line B",
          "equipment_type": "assembly",
          "location": "Factory Floor 2",
          "status": "active",
          "created_at": "2024-01-15T10:30:00Z"
        }
        ```
        """,
        "tags": ["Equipments"],
        "responses": {
            "201": {
                "description": "Equipment created successfully",
            },
            "409": {
                "description": "Equipment with this name already exists",
            },
        },
    }

    # ========================================================================
    # Cycle Endpoints Documentation
    # ========================================================================

    CYCLES_GET = {
        "summary": "Get cycles for equipment",
        "description": """
        Retrieve cycle data for a specific equipment with optional filtering.

        ### Query Parameters:
        - `equipment_id` (required): Equipment identifier
        - `start_time` (optional): Filter cycles starting after this timestamp
        - `end_time` (optional): Filter cycles starting before this timestamp
        - `status` (optional): Filter by status (normal, too_long, too_short)
        - `limit` (optional): Maximum results (default: 100, max: 10000)

        ### Filtering Algorithm:
        1. Match equipment_id exactly
        2. If start_time provided: cycle.start_time >= start_time
        3. If end_time provided: cycle.start_time <= end_time
        4. If status provided: cycle.status == status
        5. Sort by start_time descending (newest first)
        6. Apply limit

        ### Time Range Example:
        To get last 24 hours of cycles:
        - start_time = now() - 24 hours
        - end_time = now()

        ### Example:
        ```bash
        curl -X GET "http://localhost:8000/api/cycles/1?start_time=2024-01-01T00:00:00Z&limit=100"
        ```

        ### Response:
        ```json
        [
          {
            "id": 1001,
            "equipment_id": 1,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T10:05:30Z",
            "cycle_duration": 330.5,
            "status": "normal",
            "detection_method": "signal",
            "confidence": 1.0
          }
        ]
        ```
        """,
        "tags": ["Cycles"],
        "responses": {
            "200": {
                "description": "List of cycles",
            },
            "404": {
                "description": "Equipment not found",
            },
        },
    }

    # ========================================================================
    # Alert Endpoints Documentation
    # ========================================================================

    ALERTS_GET = {
        "summary": "Get alerts",
        "description": """
        Retrieve alert records with optional filtering.

        ### Query Parameters:
        - `equipment_id` (optional): Filter by equipment
        - `acknowledged` (optional): Filter by acknowledgment status
        - `severity` (optional): Filter by severity (warning, critical)
        - `limit` (optional): Maximum results (default: 100, max: 10000)

        ### Severity Levels:
        - `warning`: Cycle slightly outside threshold (recoverable)
        - `critical`: Cycle significantly outside threshold (requires attention)

        ### Alert Types:
        - `cycle_too_long`: Cycle duration exceeds maximum threshold
        - `cycle_too_short`: Cycle duration below minimum threshold

        ### Example:
        ```bash
        curl -X GET "http://localhost:8000/api/alerts?equipment_id=1&acknowledged=false&limit=50"
        ```

        ### Response:
        ```json
        [
          {
            "id": 1,
            "equipment_id": 1,
            "alert_type": "cycle_too_long",
            "severity": "warning",
            "message": "Cycle time too long: 350.2s (maximum: 300s)",
            "cycle_time": 350.2,
            "threshold_max": 300,
            "is_acknowledged": false,
            "created_at": "2024-01-15T10:05:30Z"
          }
        ]
        ```
        """,
        "tags": ["Alerts"],
        "responses": {
            "200": {
                "description": "List of alerts",
            },
        },
    }

    ALERTS_ACKNOWLEDGE = {
        "summary": "Acknowledge an alert",
        "description": """
        Mark an alert as acknowledged by a user.

        ### Fields:
        - `acknowledged_by` (required): Username or system identifier
        - `notes` (optional): Notes about the acknowledgment

        ### Side Effects:
        - Sets `is_acknowledged = true`
        - Records timestamp and user
        - Alert no longer appears in "unacknowledged" lists

        ### Example:
        ```bash
        curl -X POST "http://localhost:8000/api/alerts/1/acknowledge" \\
          -H "Content-Type: application/json" \\
          -d '{
            "acknowledged_by": "operator@factory.com",
            "notes": "Adjusted pressure valve, cycle duration normalized"
          }'
        ```

        ### Response:
        ```json
        {
          "id": 1,
          "equipment_id": 1,
          "is_acknowledged": true,
          "acknowledged_by": "operator@factory.com",
          "acknowledged_at": "2024-01-15T10:10:00Z"
        }
        ```
        """,
        "tags": ["Alerts"],
        "responses": {
            "200": {
                "description": "Alert acknowledged",
            },
            "404": {
                "description": "Alert not found",
            },
        },
    }

    # ========================================================================
    # Timeseries Endpoints Documentation
    # ========================================================================

    TIMESERIES_POST = {
        "summary": "Ingest timeseries data",
        "description": """
        Ingest time series data from sensors or PLCs.

        This endpoint accepts raw sensor data that will be used for:
        1. Real-time monitoring dashboards
        2. Cycle detection algorithms
        3. Anomaly detection
        4. Historical analysis

        ### Data Format:
        Each data point contains:
        - `equipment_id`: Which equipment the reading is from
        - `timestamp`: When the reading was taken (ISO 8601)
        - `signal_name`: Name of the signal (e.g., "motor_speed", "pressure")
        - `data_point`: Numeric value of the measurement
        - `unit`: Unit of measurement (optional, for documentation)

        ### Frequency:
        - Expected: 1-100 samples per second per equipment
        - Batch size: Up to 1000 points per request
        - Latency: <100ms processing time

        ### Example:
        ```bash
        curl -X POST "http://localhost:8000/api/timeseries" \\
          -H "Content-Type: application/json" \\
          -d '[
            {
              "equipment_id": 1,
              "timestamp": "2024-01-15T10:00:00.000Z",
              "signal_name": "motor_speed",
              "data_point": 1500.0,
              "unit": "RPM"
            },
            {
              "equipment_id": 1,
              "timestamp": "2024-01-15T10:00:01.000Z",
              "signal_name": "motor_speed",
              "data_point": 1510.0,
              "unit": "RPM"
            }
          ]'
        ```

        ### Response:
        ```json
        {
          "ingested": 2,
          "errors": 0,
          "message": "Successfully ingested 2 data points"
        }
        ```

        ### Error Handling:
        - Partial failures: Returns 207 Multi-Status with details
        - Invalid timestamp: Returns 400 Bad Request
        - Equipment not found: Returns 404 Not Found
        """,
        "tags": ["Timeseries"],
        "responses": {
            "201": {
                "description": "Data ingested successfully",
            },
            "207": {
                "description": "Partial failure - some data points rejected",
            },
            "400": {
                "description": "Invalid request format",
            },
        },
    }

    # ========================================================================
    # WebSocket Documentation
    # ========================================================================

    WEBSOCKET_REALTIME = {
        "summary": "Real-time updates (global stream)",
        "description": """
        WebSocket endpoint for global real-time stream of all events.

        ### Connection:
        ```javascript
        const ws = new WebSocket('ws://localhost:8000/ws/realtime');

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          console.log('Event:', data);
        };
        ```

        ### Message Format:
        ```json
        {
          "type": "cycle_completed|alert_created|data_point",
          "timestamp": "2024-01-15T10:05:30Z",
          "equipment_id": 1,
          "data": { ... }
        }
        ```

        ### Event Types:
        - `cycle_completed`: New cycle detected and recorded
        - `alert_created`: New alert generated
        - `data_point`: Raw sensor data (high frequency)
        - `alert_acknowledged`: Alert acknowledged by user

        ### Performance:
        - Latency: <50ms from event to client
        - Throughput: 100+ concurrent connections
        - Compression: Automatic gzip for large messages
        """,
        "tags": ["WebSocket"],
    }

    WEBSOCKET_EQUIPMENT = {
        "summary": "Equipment-specific real-time updates",
        "description": """
        WebSocket endpoint for equipment-specific event stream.

        Only receives events for the specified equipment, reducing
        bandwidth and filtering client-side.

        ### Connection:
        ```javascript
        const ws = new WebSocket('ws://localhost:8000/ws/equipment/1');

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          console.log('Equipment 1 event:', data);
        };
        ```

        ### Filtered Events:
        Only events for equipment_id=1 are sent.

        ### Use Cases:
        - Single machine monitoring dashboard
        - Operator-specific alert notifications
        - Real-time cycle updates for one line
        """,
        "tags": ["WebSocket"],
    }


class ErrorResponseSchema(BaseModel):
    """Standard error response schema."""

    error: Dict[str, str] = Field(
        example={
            "code": "VALIDATION_ERROR",
            "message": "Invalid equipment_id format",
            "details": "Expected integer, got string"
        }
    )


class PaginationSchema(BaseModel):
    """Standard pagination schema for list responses."""

    total: int = Field(description="Total number of items available")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Number of items returned")
    has_more: bool = Field(description="Whether more items are available")


def get_openapi_tags() -> List[Dict[str, Any]]:
    """
    Get OpenAPI tags with descriptions.

    Tags help organize endpoints in the API documentation.

    Returns:
        List of tag definitions for OpenAPI specification
    """
    return [
        {
            "name": "Equipments",
            "description": "Equipment management endpoints",
            "externalDocs": {
                "description": "Equipment documentation",
                "url": "https://docs.example.com/equipments",
            },
        },
        {
            "name": "Cycles",
            "description": "Cycle detection and retrieval endpoints",
        },
        {
            "name": "Alerts",
            "description": "Alert management and acknowledgment endpoints",
        },
        {
            "name": "Timeseries",
            "description": "Raw sensor data ingestion endpoints",
        },
        {
            "name": "Product Types",
            "description": "Product type configuration endpoints",
        },
        {
            "name": "Cycle Configurations",
            "description": "Cycle detection configuration endpoints",
        },
        {
            "name": "WebSocket",
            "description": "Real-time WebSocket endpoints",
        },
    ]
