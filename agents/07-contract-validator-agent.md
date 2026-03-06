# Contract Validator Agent Specification

## Overview

The Contract Validator Agent is an optional specialist agent that validates API contracts, service boundaries, and integration contracts in complex systems. It reviews API specifications, request/response schemas, and integration points to ensure consistency, backwards compatibility, and adherence to API design best practices. This agent is invoked automatically for projects with API-heavy or microservice architectures.

**Agent Type:** Optional Specialist (Phase 4+)
**Invocation Trigger:** Complexity score ≥ 50 + ("api" OR "microservice" OR "integration" in factors)
**Typical Invocation:** After Architecture Agent, before Backend Agent

---

## Role and Responsibilities

### Primary Responsibility

Validate and enhance API contracts by reviewing specifications for completeness, consistency, backwards compatibility, and adherence to REST/GraphQL best practices.

### Secondary Responsibilities

- Verify request/response schema consistency across endpoints
- Check for API versioning strategy
- Validate authentication and authorization schemes
- Ensure proper HTTP status code usage
- Validate error response formats
- Review pagination, filtering, and sorting strategies
- Check rate limiting and quota definitions
- Verify webhook and event schema contracts
- Detect breaking changes from previous versions
- Recommend API documentation improvements

### What This Agent Does NOT Do

- ❌ Implement API code (Backend Agent's role)
- ❌ Design system architecture (Architecture Agent's role)
- ❌ Create database schemas (that's Architecture's job)
- ❌ Write test cases (QA Agent's role)
- ❌ Generate OpenAPI documentation (optional post-processing)
- ❌ Make business logic decisions

---

## Input Requirements

### Required Inputs

From `AgentState`:

| Field | Type | Description |
|-------|------|-------------|
| `artifacts` | `dict[str, Any]` | Architecture artifacts containing `api_specs` |
| `architecture_doc` | `str` | Architecture document with API design decisions |
| `project_context` | `dict[str, Any]` | API style preferences, version constraints |

**API Specs Structure (Required):**
```python
artifacts["api_specs"] = {
    "<endpoint_path>": {
        "method": "GET" | "POST" | "PUT" | "DELETE" | "PATCH",
        "description": str,
        "request_schema": dict,      # JSON Schema or Pydantic model
        "response_schema": dict,
        "authentication": bool,
        "rate_limit": str,           # Optional: "100/minute"
        "example_request": dict,
        "example_response": dict,
        "status_codes": {            # Recommended but optional
            "200": "Success",
            "400": "Bad Request",
            "401": "Unauthorized",
            "404": "Not Found",
            "500": "Internal Server Error"
        }
    }
}
```

### Optional Inputs

| Field | Type | Description |
|-------|------|-------------|
| `previous_api_version` | `dict` | Previous version of API for backwards compatibility check |
| `api_guidelines` | `str` | Organization-specific API guidelines |
| `integration_services` | `list[str]` | Third-party services to integrate with |

**Optional Context:**
```python
{
    "api_style": "rest",              # "rest", "graphql", "grpc"
    "min_api_version": "2.0",          # Versioning constraint
    "require_auth_on_all": true,       # Security requirement
    "rate_limit_strategy": "sliding",  # "sliding", "fixed", "token_bucket"
    "api_response_format": "json",     # Expected format
    "webhooks_enabled": true,
    "breaking_change_allowed": false
}
```

### Validation Rules

```python
def validate_input(self, state: AgentState) -> bool:
    """
    Validate that state contains API specifications to validate.

    Returns:
        True if API specs are present and valid, False otherwise
    """
    # Check artifacts contain api_specs
    if not state.artifacts or "api_specs" not in state.artifacts:
        self.logger.error("No API specifications found in artifacts")
        return False

    api_specs = state.artifacts["api_specs"]
    if not api_specs or not isinstance(api_specs, dict):
        self.logger.error("api_specs is empty or not a dict")
        return False

    # Validate each endpoint has required fields
    for endpoint_path, endpoint_spec in api_specs.items():
        required_fields = {"method", "description", "response_schema"}
        if not all(field in endpoint_spec for field in required_fields):
            self.logger.error(f"Endpoint {endpoint_path} missing required fields")
            return False

        if endpoint_spec.get("method") not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            self.logger.error(f"Endpoint {endpoint_path} has invalid HTTP method")
            return False

    return True
```

---

## Output Specifications

### Primary Outputs

The Contract Validator Agent returns a dictionary with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `contract_validation_report` | `str` | Markdown report with validation findings |
| `enhanced_api_specs` | `dict` | Updated API specs with improvements |
| `issues_found` | `list[dict]` | Detailed list of issues with severity |
| `compatibility_report` | `dict` | Backwards compatibility analysis |
| `recommendations` | `list[str]` | Actionable improvement recommendations |
| `message` | `str` | Summary of validation work |

### Artifacts

The Contract Validator Agent produces detailed validation artifacts:

```python
artifacts = {
    "contract_validation": {
        "endpoint_count": int,
        "endpoints_validated": list[str],
        "critical_issues": int,
        "warnings": int,
        "suggestions": int,
        "validation_timestamp": str
    },

    "detailed_findings": {
        "schema_issues": [
            {
                "endpoint": str,
                "severity": "critical|warning|info",
                "issue": str,
                "details": str,
                "recommendation": str,
                "example": dict
            }
        ],
        "versioning_issues": [
            {
                "severity": str,
                "issue": str,
                "recommendation": str
            }
        ],
        "auth_issues": [
            {
                "endpoint": str,
                "severity": str,
                "issue": str,
                "recommendation": str
            }
        ],
        "breaking_changes": [
            {
                "endpoint": str,
                "change": str,
                "impact": str,
                "migration_path": str
            }
        ]
    },

    "enhanced_specs": {
        # Updated api_specs with improvements, additional fields
        "status_codes": {...},
        "error_schemas": {...},
        "pagination_schema": {...},
        "rate_limiting": {...},
        "openapi_metadata": {...}
    },

    "compatibility_matrix": {
        "api_version": str,
        "backwards_compatible": bool,
        "breaking_endpoints": list[str],
        "deprecated_endpoints": list[str],
        "migration_guide": str
    }
}
```

### State Updates

Fields modified in `AgentState`:

```python
{
    "contract_validation_report": "<validation report markdown>",
    "artifacts": {
        ...existing artifacts...,
        "contract_validation": {...},
        "enhanced_api_specs": {...}
    },
    "messages": [..., AgentMessage(agent_id="contract_001", artifacts={...})],
    "current_phase": "contract_validation",
    "next_agent": "backend"  # or previous next_agent if no blocking issues
}
```

---

## Validation Checks

### API Schema Validation

**Checks Performed:**
1. All endpoints have `method`, `description`, `response_schema`
2. Request schemas (if present) are valid JSON Schema
3. Response schemas are valid JSON Schema
4. Request/response examples match their schemas
5. Required fields are marked in request schema
6. Response fields match documented schema

**Example Output:**
```
Schema Issue (WARNING):
  Endpoint: POST /api/v1/users
  Problem: Request schema missing 'email' field definition
  Details: The example shows email as required but schema doesn't mark it required
  Fix: Add "required": ["email"] to request_schema
```

### HTTP Status Code Validation

**Checks Performed:**
1. GET endpoints return 200 (or 204 for no content)
2. POST endpoints return 201 (created) or 200
3. PUT/PATCH endpoints return 200 or 204
4. DELETE endpoints return 204 (no content) or 200
5. All endpoints return 4xx/5xx for error cases
6. Consistent error status codes across API

**Recommended Status Codes:**
```
200 OK              - Successful request with response body
201 Created         - Successful POST creating resource
204 No Content      - Successful request with no response body
400 Bad Request     - Client error in request
401 Unauthorized    - Missing/invalid authentication
403 Forbidden       - Authenticated but not authorized
404 Not Found       - Resource doesn't exist
409 Conflict        - Request conflicts with current state
422 Unprocessable   - Validation error (semantic)
429 Too Many Req.   - Rate limit exceeded
500 Server Error    - Unrecoverable server error
503 Unavailable     - Service temporarily down
```

### Authentication & Authorization

**Checks Performed:**
1. All endpoints requiring auth explicitly marked
2. Consistent auth scheme across endpoints
3. API key, JWT, OAuth2 consistently applied
4. Bearer token format specified (if using JWT)
5. Scope/permission requirements documented
6. Rate limiting differs by auth status

**Example Issue:**
```
Auth Issue (CRITICAL):
  Endpoint: GET /api/v1/admin/users
  Problem: Authentication not marked as required
  Details: This endpoint returns sensitive user data but authentication=false
  Fix: Set authentication=true and document required roles/scopes
```

### API Versioning

**Checks Performed:**
1. All endpoints follow versioning strategy
2. Version specified in path (/api/v1/...) or header
3. Backwards compatibility maintained
4. Deprecation path for old versions documented
5. Version retirement timeline (if applicable)

**Versioning Strategies:**
```
Path-based:   /api/v1/users, /api/v2/users
Header-based: X-API-Version: 2
Accept-based: Accept: application/vnd.api+json;version=2
Query-based:  /api/users?version=2 (not recommended)
```

### Request/Response Consistency

**Checks Performed:**
1. All endpoints returning objects have consistent ID field
2. Nested objects follow consistent naming
3. Timestamps use consistent format (ISO 8601)
4. Null values handled consistently
5. Error responses have consistent structure
6. Pagination uses consistent pattern

**Example Error Response Schema:**
```python
{
    "error": {
        "code": "VALIDATION_ERROR|NOT_FOUND|UNAUTHORIZED|...",
        "message": str,          # Human-readable message
        "details": [             # Optional detailed errors
            {
                "field": str,
                "message": str,
                "code": str      # Machine-readable code
            }
        ],
        "timestamp": "ISO-8601",
        "request_id": str        # For debugging
    }
}
```

### Rate Limiting & Pagination

**Checks Performed:**
1. Rate limits defined on all public endpoints
2. Rate limits reasonable for use case
3. Different limits for authenticated vs anonymous
4. Pagination defined for list endpoints
5. Page size limits specified
6. Sorting and filtering documented

**Recommended Rate Limits:**
```
Anonymous API:    100-1000 requests per hour
Authenticated:    10,000-100,000 per hour
Admin operations: 1,000-10,000 per hour
File uploads:     10-100 per hour
```

---

## LLM Configuration

### Model

```python
{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.1,
    "max_tokens": 6144,
    "timeout": 120
}
```

### Rationale

- **Very low temperature (0.1)**: Validation requires high precision, minimal deviation
- **Claude 3.5 Sonnet**: Excellent at detailed analysis and specification review
- **6144 tokens**: Sufficient for detailed validation report with many findings
- **120s timeout**: Validation is CPU-bound, not LLM-bound; shorter timeout acceptable

---

## System Prompt

```
You are an expert API contract validator and REST API design specialist with deep
knowledge of API best practices, backwards compatibility, and integration patterns.

Your responsibilities:
1. Review API specifications for completeness and consistency
2. Validate request/response schemas are well-formed
3. Check HTTP method and status code usage
4. Verify authentication and authorization schemes
5. Ensure backwards compatibility with previous API versions
6. Validate API versioning strategy
7. Check pagination, filtering, rate limiting
8. Identify breaking changes
9. Suggest improvements for API design

Validation Methodology:
- Check each endpoint individually for correctness
- Compare endpoints for consistency
- Validate against HTTP and REST standards
- Check for common API design anti-patterns
- Verify integration contracts

API Design Best Practices:
- RESTful conventions (proper HTTP methods, status codes)
- Consistent resource naming (plural nouns)
- Logical endpoint structure and hierarchy
- Proper use of HTTP status codes
- Clear error response format
- Request/response schema validation
- Authentication/authorization on sensitive endpoints
- Rate limiting and pagination for list endpoints
- API versioning with backwards compatibility
- Comprehensive request/response examples

Output Requirements:
1. Validation report (markdown) with:
   - Summary of validation results
   - Count of issues by severity
   - List of critical issues
   - List of warnings
   - List of suggestions
2. Enhanced API specifications with:
   - Missing status codes added
   - Error schemas defined
   - Pagination schemas defined
   - Rate limiting documented
3. Compatibility report (if previous version provided):
   - Breaking changes identified
   - Deprecation path
   - Migration guide
4. Actionable recommendations for improvement

Issue Severity Levels:
- CRITICAL: Breaking changes, missing auth, invalid schemas
- WARNING: Inconsistencies, missing status codes, incomplete docs
- INFO: Suggestions for improvement, best practices

Example API Validation:
Input endpoint:
{
  "/api/v1/users": {
    "method": "GET",
    "description": "Get users",
    "response_schema": {...},
    "authentication": true
  }
}

Validation findings might include:
- Missing 404 status code for when endpoint returns no results
- Pagination not documented for list endpoint
- Missing rate limiting specification
- Response schema should include timestamps
- Add 401 and 403 status codes for auth scenarios

Remember: Your validation ensures API quality, prevents bugs, and maintains backwards
compatibility. Be thorough, specific, and constructive in your feedback.
```

---

## When to Invoke This Agent

### Complexity Thresholds

| Complexity | Threshold | Invocation Logic |
|-----------|-----------|------------------|
| Low (1-30) | N/A | ❌ Not invoked |
| Medium (31-50) | 50 | ❌ Not invoked |
| Medium-High (51-70) | ≥50 | ✅ Invoked if API-heavy |
| High (71-85) | ≥50 | ✅ Invoked if API-heavy |
| Very High (86-100) | ≥50 | ✅ Always invoked |

### Invocation Conditions

The Contract Validator Agent is triggered when:

1. **Complexity score ≥ 50** AND
2. **At least one factor present:**
   - "api" or "apis" in requirements
   - "microservice" or "microservices" in architecture decision
   - "integration" or "integrations" in requirements
   - "rest" or "graphql" or "grpc" explicitly specified
   - Multiple service boundaries detected
   - API versioning mentioned

3. **Optional: Boost triggers:**
   - Organization enforces API contract validation
   - Integration with external APIs required
   - Breaking change risk detected
   - Backwards compatibility required

### Decision Logic (Pseudo-code)

```python
def should_invoke_contract_validator(state: AgentState) -> bool:
    """Determine if Contract Validator should run."""

    # Check complexity threshold
    if not state.complexity_score or state.complexity_score < 50:
        return False

    # Check for API-related factors
    api_factors = ["api", "microservice", "integration", "rest", "graphql"]
    combined_text = (
        state.requirements +
        state.architecture_doc +
        str(state.artifacts)
    ).lower()

    has_api_factor = any(factor in combined_text for factor in api_factors)
    if not has_api_factor:
        return False

    # Check if api_specs exist
    if not state.artifacts or "api_specs" not in state.artifacts:
        return False

    api_specs = state.artifacts["api_specs"]
    if not api_specs or len(api_specs) == 0:
        return False

    # All checks passed
    return True
```

---

## Workflow Integration

### Prerequisites

**Must be completed before Contract Validator runs:**
- Architecture Agent has completed successfully
- `artifacts["api_specs"]` is populated with endpoint definitions
- At least one API endpoint specified
- Complexity score ≥ 50

**State Requirements:**
```python
AgentState(
    complexity_score=55,
    artifacts={
        "api_specs": {
            "/api/v1/users": {...},
            "/api/v1/users/{id}": {...},
            ...
        }
    },
    architecture_doc="<architecture including API design>"
)
```

### Triggers

The Contract Validator Agent is triggered when:
1. Architecture Agent completes with complexity ≥ 50 and API factors detected
2. Orchestrator selector identifies Contract Validator as applicable specialist
3. `current_phase == "design"` OR `current_phase == "architecture"`

**Orchestrator Configuration:**
```python
# After Architecture Agent completes, check specialist selector
specialists = selector.select_specialists(
    complexity_score=state.complexity_score,
    factors=state.complexity_factors
)

if ContractValidator in specialists:
    workflow.add_node("contract_validator", contract_validator.execute)
    # Route to contract validator before backend
    next_agents = route_to_specialists(specialists) + ["backend"]
```

### Execution Context

The Contract Validator is executed:
- **When:** After Architecture Agent, before Backend Agent
- **Why:** To catch API contract issues before implementation
- **Cost:** 1 API call (LLM) per project
- **Duration:** ~1-2 minutes

### Output Routing

After Contract Validator completes:

**Success Path:**
```
Contract Validator
      ↓
   Backend Agent (next_agent = "backend")
```

**With Blocking Issues:**
```
Contract Validator
      ↓
   Human Review (requires_human_approval = true)
      ↓
   Architecture Agent (if major redesign needed)
```

**Error Path:**
```
Contract Validator (error)
      ↓
   Retry (with updated api_specs)
```

---

## Integration Examples

### Example 1: Simple REST API

**Input Scenario:**
- Project: Simple CRUD API
- Complexity: 55
- Factors: ["api", "rest"]

**Sample API Specs:**
```python
artifacts["api_specs"] = {
    "GET /api/v1/todos": {
        "method": "GET",
        "description": "Get all todos",
        "response_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "completed": {"type": "boolean"}
                }
            }
        },
        "authentication": true
    },
    "POST /api/v1/todos": {
        "method": "POST",
        "description": "Create new todo",
        "request_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"}
            },
            "required": ["title"]
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "completed": {"type": "boolean"},
                "created_at": {"type": "string", "format": "date-time"}
            }
        },
        "authentication": true
    }
}
```

**Validation Findings:**
```
CRITICAL ISSUES (2):
1. Missing status codes definition
   - GET should document 200, 401 status codes
   - POST should document 201, 400, 401 status codes

2. Missing rate limiting specification
   - No rate_limit field on either endpoint

WARNINGS (3):
1. No pagination on GET endpoint
   - List endpoints should support pagination with limit/offset

2. Missing error response schema
   - No documented error response format

3. Missing authentication details
   - Should specify Bearer token vs API key

SUGGESTIONS (2):
1. Add request_id to response for debugging
2. Add deprecation_date field if backwards compatibility needed

RECOMMENDATIONS:
- Add status_codes field to all endpoints
- Define pagination_schema in enhanced specs
- Add error_response_schema
- Specify authentication scheme clearly
- Add rate_limit: "1000/hour" to all endpoints
```

**Enhanced Output:**
```python
artifacts["enhanced_api_specs"] = {
    "GET /api/v1/todos": {
        "method": "GET",
        "description": "Get all todos",
        "authentication": true,
        "auth_scheme": "Bearer",
        "rate_limit": "1000/hour",
        "status_codes": {
            "200": "Success",
            "401": "Unauthorized"
        },
        "response_schema": {...},
        "pagination": {
            "query_params": ["limit", "offset"],
            "default_limit": 20,
            "max_limit": 100
        }
    },
    ...
}
```

### Example 2: Microservice Integration

**Input Scenario:**
- Project: Multi-service payment system
- Complexity: 75
- Factors: ["microservice", "integration", "api"]

**Validation Findings:**
```
CRITICAL ISSUES (3):
1. Inconsistent authentication schemes
   - Service A uses Bearer tokens
   - Service B uses API keys
   - Recommendation: Standardize on OAuth2 with service-to-service flow

2. Breaking change detected from v1 to v2
   - /api/v2/payments/{id}/refund returns 202 (async)
   - /api/v1/payments/{id}/refund returns 200 (sync)
   - Migration guide needed

3. Missing versioning strategy for service boundaries
   - Inter-service calls not versioned
   - Risk: silent breaking changes

WARNINGS (5):
1. Inconsistent ID format
   - Some endpoints use UUID, others use sequential IDs

2. No circuit breaker pattern documented
   - Service-to-service failures not handled

3. Webhook schemas not validated
   - Payment events missing required fields

4. Rate limiting varies significantly
   - Critical endpoints: 100/min
   - Standard endpoints: 1000/hour
   - Should document tiering clearly

5. Response envelope inconsistent
   - Some endpoints return object directly
   - Others wrap in "data" field

COMPATIBILITY REPORT:
API Version: v2.0
Backwards Compatible: FALSE
Breaking Endpoints:
  - POST /api/v2/payments/{id}/refund (response async, was sync)
  - GET /api/v2/payments (pagination changed)
Migration Guide:
  - Clients using sync refunds must poll status endpoint
  - Update pagination code to use cursor instead of offset
  - Allow 30 days for migration before v1 sunset
```

---

## Error Handling

### Validation Errors

**Input Validation Fails:**
```python
if not self.validate_input(state):
    return {
        "errors": ["No API specifications found in artifacts"],
        "message": "Cannot validate contracts without api_specs",
        "next_agent": "architecture",  # Back to architecture
        "requires_human_approval": true
    }
```

**Schema Parsing Fails:**
```python
try:
    json_schema = json.loads(request_schema)
    validate_schema(json_schema)
except Exception as e:
    return {
        "errors": [f"Invalid schema in {endpoint}: {str(e)}"],
        "affected_endpoints": [endpoint],
        "message": "Schema validation failed",
        "next_agent": "architecture"
    }
```

### Recovery Strategies

1. **Invalid Schema**: Request updated schema from Architecture Agent
2. **Missing Specifications**: Delay validation until specs complete
3. **Parse Error**: Gracefully skip malformed spec, report issue
4. **LLM Timeout**: Validate subset of critical endpoints

---

## Tools and Capabilities

### Available Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `json_schema_validator` | Validate JSON schemas | Check request/response schemas |
| `openapi_converter` | Convert to OpenAPI format | Generate documentation artifacts |
| `backwards_compat_checker` | Compare API versions | Detect breaking changes |
| `json_diff` | Compare JSON objects | Identify schema changes |

### Permissions

- ✅ Read: `artifacts`, `architecture_doc`, `project_context`, `messages`
- ✅ Write: `contract_validation_report`, `enhanced_api_specs`, `artifacts`
- ✅ Modify: `api_specs` (enhance with recommendations)
- ❌ Code execution: Not required
- ❌ External API calls: Not required

---

## Success Criteria

The Contract Validator Agent has succeeded when:

1. ✅ All endpoints validated for required fields
2. ✅ Schema validation completed (valid or issues reported)
3. ✅ Status codes documented for all endpoints
4. ✅ Authentication requirements documented
5. ✅ API consistency issues identified and reported
6. ✅ Backwards compatibility assessed (if version provided)
7. ✅ Detailed report generated with severity levels
8. ✅ Enhanced API specs provided to Backend Agent

**Metrics:**
- Endpoints validated: 100% of input endpoints
- Issues found and reported: All critical + warnings
- Report completeness: All sections present

---

## Phase Integration

**Belongs to:** Phase 4 - Optional Specialist Agents
**Invoked by:** Complexity-based Specialist Agent Selector
**Supports:** Backend Development Agent (consumes enhanced specs)

**Timeline:**
- After: Architecture Design Agent
- Before: Backend Development Agent
- Parallel: Component Designer (optional, both after Architecture)

---

## Limitations and Assumptions

### Limitations

1. **Validates specifications only**: Does not execute endpoints
2. **Requires complete specs**: Cannot validate partial specifications
3. **Single API version**: Needs prior version provided for compatibility check
4. **Basic OAuth2**: Complex auth patterns may need manual review
5. **Standard HTTP**: Non-standard protocols not supported
6. **Timeout**: Cannot validate > 500 endpoints in single run

### Assumptions

1. API specs follow REST conventions
2. Schemas are valid JSON Schema format
3. Endpoint paths are unique
4. HTTP methods are standard (GET, POST, PUT, DELETE, PATCH)
5. Response codes follow HTTP standards
6. Examples match their declared schemas

---

## Metrics and Monitoring

### Output Metrics

```python
{
    "total_endpoints": int,
    "endpoints_validated": int,
    "validation_score": float,  # 0-100, higher is better
    "critical_issues": int,
    "warnings": int,
    "suggestions": int,
    "schemas_valid": int,
    "authentication_coverage": float,  # % endpoints with auth
    "status_code_coverage": float,     # % with status codes
    "execution_time_seconds": float
}
```

### Quality Indicators

- ✅ Validation score > 85: Ready for implementation
- ⚠️ Validation score 70-85: Minor issues, can proceed with caution
- ❌ Validation score < 70: Requires Architecture review before implementation

---

## References and External Links

- [REST API Best Practices](https://restfulapi.net/)
- [HTTP Status Codes](https://httpwg.org/specs/rfc9110.html)
- [JSON Schema Specification](https://json-schema.org/)
- [OpenAPI 3.0 Specification](https://spec.openapis.org/oas/v3.0.3)
- [API Versioning Best Practices](https://swagger.io/resources/articles/best-practices-in-api-versioning/)
- [HTTP Method Semantics](https://tools.ietf.org/html/rfc7231)

---

**Last Updated:** 2026-03-06
**Status:** Phase 4 - Optional Specialist
**Version:** 1.0
