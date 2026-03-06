# API Reference - Universal Agent Team

Complete REST API documentation with examples.

## Base URL

```
http://localhost:8000  (Development)
https://api.example.com (Production)
```

## Authentication

All endpoints require an API key in the `Authorization` header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/projects
```

## Table of Contents

1. [Projects](#projects)
2. [Agents](#agents)
3. [Artifacts](#artifacts)
4. [Health & Monitoring](#health--monitoring)
5. [Error Responses](#error-responses)

---

## Projects

### Create Project

**POST** `/api/projects`

Create a new project and start execution.

**Request Body:**
```json
{
  "user_request": "Build a todo list application with React and FastAPI",
  "team_id": "universal-agents-v1",
  "metadata": {
    "client_name": "Acme Corp",
    "project_context": "Internal tool"
  }
}
```

**Response (201 Created):**
```json
{
  "project_id": "proj_550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-03-06T10:00:00Z",
  "user_request": "Build a todo list application with React and FastAPI"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-ant-..." \
  -d '{
    "user_request": "Build a todo app",
    "team_id": "universal-agents-v1"
  }'
```

---

### List Projects

**GET** `/api/projects`

List all projects with optional filtering.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | - | Filter by status (pending, in_progress, complete, error) |
| `team_id` | string | - | Filter by team |
| `skip` | integer | 0 | Number of projects to skip |
| `limit` | integer | 50 | Max projects to return (max 100) |

**Response:**
```json
{
  "items": [
    {
      "project_id": "proj_550e8400-e29b-41d4-a716-446655440000",
      "status": "complete",
      "created_at": "2026-03-06T10:00:00Z",
      "updated_at": "2026-03-06T10:30:00Z",
      "user_request": "Build a todo list application..."
    }
  ],
  "total": 25,
  "skip": 0,
  "limit": 50
}
```

**Example:**
```bash
# List all projects
curl http://localhost:8000/api/projects

# Filter by status
curl "http://localhost:8000/api/projects?status=complete"

# Pagination
curl "http://localhost:8000/api/projects?skip=50&limit=25"
```

---

### Get Project Details

**GET** `/api/projects/{project_id}`

Get detailed information about a project.

**Response:**
```json
{
  "project_id": "proj_550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "current_phase": "frontend",
  "progress_percent": 65,
  "created_at": "2026-03-06T10:00:00Z",
  "updated_at": "2026-03-06T10:20:00Z",
  "user_request": "Build a todo list application with React and FastAPI",
  "team_id": "universal-agents-v1",
  "phases": {
    "planning": {
      "status": "complete",
      "duration_ms": 500,
      "output": "Created requirement specifications"
    },
    "architecture": {
      "status": "complete",
      "duration_ms": 800,
      "output": "Designed microservices architecture"
    },
    "frontend": {
      "status": "in_progress",
      "duration_ms": 3500,
      "output": ""
    }
  },
  "errors": []
}
```

**Example:**
```bash
curl http://localhost:8000/api/projects/proj_550e8400-e29b-41d4-a716-446655440000
```

---

### Update Project

**PATCH** `/api/projects/{project_id}`

Update project metadata.

**Request Body:**
```json
{
  "metadata": {
    "priority": "high",
    "assigned_to": "john@example.com"
  }
}
```

**Response:**
```json
{
  "project_id": "proj_550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "metadata": {
    "priority": "high",
    "assigned_to": "john@example.com"
  }
}
```

---

### Cancel Project

**POST** `/api/projects/{project_id}/cancel`

Stop execution of a running project.

**Response:**
```json
{
  "project_id": "proj_550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "cancelled_at": "2026-03-06T10:25:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/projects/proj_550e8400-e29b-41d4-a716-446655440000/cancel
```

---

### Delete Project

**DELETE** `/api/projects/{project_id}`

Delete a project and all associated artifacts.

**Response:**
```json
{
  "success": true,
  "deleted_count": 1,
  "artifacts_deleted": 127
}
```

---

## Artifacts

### Get Project Artifacts

**GET** `/api/projects/{project_id}/artifacts`

Download all generated artifacts as a ZIP file.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `format` | string | zip, json, or directory listing |

**Response:** ZIP file with project artifacts

**Structure:**
```
artifacts.zip
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── app/
│       ├── models.py
│       └── routes/
├── tests/
│   ├── frontend.test.ts
│   └── backend_test.py
├── docs/
│   ├── README.md
│   ├── API.md
│   └── DEPLOYMENT.md
└── project.json
```

**Example:**
```bash
# Download as ZIP
curl http://localhost:8000/api/projects/proj_xxx/artifacts \
  -H "Authorization: Bearer sk-ant-..." \
  -o artifacts.zip

# Or as JSON
curl "http://localhost:8000/api/projects/proj_xxx/artifacts?format=json"
```

---

### Get Specific Artifact

**GET** `/api/projects/{project_id}/artifacts/{artifact_type}`

Get a specific artifact (e.g., frontend code, backend code, docs).

**Artifact Types:**
- `frontend` - React/TypeScript code
- `backend` - Python/FastAPI code
- `tests` - Test files
- `docs` - Documentation
- `architecture` - Architecture document
- `requirements` - Requirements document

**Response:**
```json
{
  "artifact_type": "frontend",
  "files": {
    "src/components/TodoList.tsx": "export const TodoList = () => { ... }",
    "src/pages/Dashboard.tsx": "...",
    "package.json": "{ \"name\": \"todo-app\", ... }"
  },
  "generated_at": "2026-03-06T10:30:00Z"
}
```

---

### Upload Artifact

**POST** `/api/projects/{project_id}/artifacts`

Upload custom artifacts or revisions.

**Request Body:**
```json
{
  "artifact_type": "custom",
  "files": {
    "config.json": "{ \"key\": \"value\" }",
    "custom_code.py": "def my_function(): ..."
  }
}
```

---

## Agents

### List Available Agents

**GET** `/api/agents`

Get list of available agents and their capabilities.

**Response:**
```json
{
  "agents": [
    {
      "agent_id": "planning",
      "name": "Planning Agent",
      "role": "Requirements Analysis",
      "capabilities": [
        "Requirements analysis",
        "Task breakdown",
        "Dependency detection",
        "Risk assessment"
      ],
      "status": "available"
    },
    {
      "agent_id": "architecture",
      "name": "Architecture Agent",
      "role": "System Design",
      "capabilities": [
        "Architecture design",
        "Component specification",
        "API contract definition",
        "Database schema design"
      ],
      "status": "available"
    }
  ]
}
```

---

### Get Agent Details

**GET** `/api/agents/{agent_id}`

Get detailed information about a specific agent.

**Response:**
```json
{
  "agent_id": "frontend",
  "name": "Frontend Development Agent",
  "role": "UI Developer",
  "description": "Generates React/TypeScript components",
  "capabilities": [
    "React component generation",
    "TypeScript implementation",
    "Tailwind CSS styling",
    "API integration"
  ],
  "input_schema": {
    "type": "object",
    "properties": {
      "component_specs": { "type": "object" },
      "design_system": { "type": "object" },
      "api_specs": { "type": "object" }
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "code_files": { "type": "object" },
      "dependencies": { "type": "array" },
      "test_files": { "type": "object" }
    }
  }
}
```

---

### Test Agent

**POST** `/api/agents/{agent_id}/test`

Test an agent with sample input.

**Request Body:**
```json
{
  "sample_input": {
    "component_specs": {
      "TodoList": {
        "props": ["todos", "onAdd"],
        "state": ["filter"]
      }
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "execution_time_ms": 1234,
  "output": {
    "code_files": {
      "src/components/TodoList.tsx": "..."
    }
  }
}
```

---

## Health & Monitoring

### Health Check

**GET** `/health`

Quick health check (minimal latency).

**Response:**
```json
{
  "status": "healthy"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### Readiness Check

**GET** `/ready`

Detailed readiness check (includes dependencies).

**Response:**
```json
{
  "ready": true,
  "checks": {
    "database": "connected",
    "redis": "connected",
    "api": "responding",
    "queue": "operational"
  }
}
```

---

### Metrics

**GET** `/metrics`

Prometheus-format metrics for monitoring.

**Example Output:**
```
# HELP http_request_duration_seconds Request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.005",path="/health"} 950
http_request_duration_seconds_bucket{le="0.01",path="/health"} 985
http_request_duration_seconds_bucket{le="0.025",path="/health"} 995

# HELP cache_hit_rate Cache hit rate
# TYPE cache_hit_rate gauge
cache_hit_rate 0.92
```

---

## Error Responses

### Error Format

All errors follow a consistent format:

```json
{
  "detail": "Project not found",
  "error_code": "PROJECT_NOT_FOUND",
  "timestamp": "2026-03-06T10:30:00Z",
  "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
}
```

### Common Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `INVALID_REQUEST` | 400 | Invalid request body |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `PROJECT_NOT_FOUND` | 404 | Project doesn't exist |
| `INVALID_STATE_TRANSITION` | 409 | Cannot transition to requested state |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily down |

### Example Errors

**Invalid Request (400)**
```json
{
  "detail": "user_request is required",
  "error_code": "INVALID_REQUEST",
  "timestamp": "2026-03-06T10:30:00Z"
}
```

**Unauthorized (401)**
```json
{
  "detail": "Invalid or missing API key",
  "error_code": "UNAUTHORIZED",
  "timestamp": "2026-03-06T10:30:00Z"
}
```

**Not Found (404)**
```json
{
  "detail": "Project proj_xyz not found",
  "error_code": "PROJECT_NOT_FOUND",
  "timestamp": "2026-03-06T10:30:00Z"
}
```

**Rate Limited (429)**
```json
{
  "detail": "Rate limit exceeded: 10 requests per minute",
  "error_code": "RATE_LIMITED",
  "retry_after": 45,
  "timestamp": "2026-03-06T10:30:00Z"
}
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /projects` | 10 | 1 minute |
| `GET /projects` | 100 | 1 minute |
| `GET /projects/{id}` | 1000 | 1 minute |
| `GET /artifacts` | 100 | 1 minute |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 5
X-RateLimit-Reset: 1646390400
```

---

## Pagination

List endpoints support cursor-based pagination:

**Query Parameters:**
```bash
?skip=0&limit=50
```

**Response:**
```json
{
  "items": [...],
  "total": 100,
  "skip": 0,
  "limit": 50,
  "has_more": true
}
```

---

## Webhooks (Optional)

Subscribe to project completion events:

**Register Webhook:**
```bash
POST /api/webhooks
{
  "event": "project.complete",
  "url": "https://example.com/webhooks/project-complete",
  "secret": "whsec_xxx"
}
```

**Webhook Payload:**
```json
{
  "event": "project.complete",
  "project_id": "proj_xxx",
  "status": "complete",
  "artifacts_url": "https://api.example.com/projects/proj_xxx/artifacts",
  "timestamp": "2026-03-06T10:30:00Z"
}
```

---

## SDK Examples

### Python

```python
from anthropic_agents import UniversalAgentClient

client = UniversalAgentClient(api_key="sk-ant-...")

# Create project
project = client.projects.create(
    user_request="Build a todo app with React and FastAPI",
    team_id="universal-agents-v1"
)

# Wait for completion
project = client.projects.wait_for_completion(project.project_id, timeout=300)

# Download artifacts
artifacts = client.projects.download_artifacts(project.project_id, format="zip")
```

### JavaScript

```javascript
import { UniversalAgentClient } from '@anthropic/agent-client';

const client = new UniversalAgentClient({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Create project
const project = await client.projects.create({
  user_request: 'Build a todo app',
  team_id: 'universal-agents-v1',
});

// Wait for completion
const completed = await client.projects.waitForCompletion(
  project.project_id,
  { timeout: 300000 }
);

// Download artifacts
const artifacts = await client.projects.downloadArtifacts(
  project.project_id,
  { format: 'zip' }
);
```

---

**Last Updated**: 2026-03-06
**Status**: Production Ready ✓
