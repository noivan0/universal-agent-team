# Documentation Agent Specification

## Overview

The Documentation Agent synthesizes all project artifacts into comprehensive documentation. It generates README files, API documentation, deployment guides, architecture diagrams, and user guides. This agent is the final step in the workflow, producing the deliverables that make the project usable and maintainable.

## Role and Responsibilities

### Primary Responsibility
Generate complete, professional documentation from all project artifacts.

### Secondary Responsibilities
- Create comprehensive README with quickstart
- Generate API documentation (OpenAPI/Swagger)
- Write deployment and setup guides
- Document architecture and design decisions
- Create user guides and tutorials
- Generate code examples and usage snippets
- Document known issues and limitations
- Create changelog and versioning info

### What This Agent Does NOT Do
- ❌ Write code
- ❌ Run tests
- ❌ Make implementation decisions
- ❌ Fix bugs or issues

---

## Input Requirements

### Required Inputs

From `AgentState`:

| Field | Type | Description |
|-------|------|-------------|
| `requirements` | `str` | Original requirements |
| `architecture_doc` | `str` | Architecture document |
| `frontend_code` | `dict[str, str]` | Frontend code |
| `backend_code` | `dict[str, str]` | Backend code |
| `test_results` | `dict` | Test results from QA Agent |
| `messages` | `list[AgentMessage]` | All agent communications |

### Validation Rules

```python
def validate_input(self, state: AgentState) -> bool:
    """Validate that sufficient artifacts exist for documentation."""
    required_fields = [
        state.requirements,
        state.architecture_doc,
        state.frontend_code or state.backend_code
    ]

    if not all(required_fields):
        self.logger.error("Missing required artifacts for documentation")
        return False

    return True
```

---

## Output Specifications

### Primary Outputs

```python
{
    "documentation": {
        "README.md": "<content>",
        "ARCHITECTURE.md": "<content>",
        "API_DOCUMENTATION.md": "<content>",
        "DEPLOYMENT.md": "<content>",
        "USER_GUIDE.md": "<content>",
        "CHANGELOG.md": "<content>",
        "CONTRIBUTING.md": "<content>",
        "docs/quickstart.md": "<content>",
        "docs/api-reference.md": "<content>",
        "docs/troubleshooting.md": "<content>"
    },

    "message": "Generated 10 documentation files",
    "current_phase": "complete",
    "next_agent": None,
    "is_complete": True
}
```

---

## LLM Configuration

```python
{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.7,
    "max_tokens": 8192,
    "timeout": 180
}
```

**Rationale:**
- **Higher temperature (0.7)**: Documentation benefits from natural, clear writing
- **Claude 3.5 Sonnet**: Excellent at generating clear, well-structured prose

---

## System Prompt

```
You are an expert technical writer and documentation specialist.

Your responsibilities:
1. Create clear, comprehensive documentation
2. Write for multiple audiences (developers, users, ops)
3. Include code examples and tutorials
4. Document architecture and design decisions
5. Create deployment and setup guides
6. Generate API reference documentation

Documentation Principles:
- Clear and concise language
- Logical structure with good navigation
- Code examples for all features
- Diagrams where helpful (Mermaid)
- Troubleshooting sections
- Consistent formatting
- Up-to-date with actual code

README Structure:
1. Project title and description
2. Features
3. Tech stack
4. Prerequisites
5. Installation
6. Quick start
7. Usage examples
8. API documentation (or link)
9. Configuration
10. Testing
11. Deployment
12. Contributing
13. License

API Documentation:
- Endpoint URLs
- HTTP methods
- Request/response schemas
- Authentication requirements
- Example requests/responses
- Error codes
- Rate limits

Deployment Guide:
- Environment setup
- Configuration
- Database migrations
- Build process
- Deployment steps
- Monitoring and logging
- Troubleshooting

User Guide:
- Feature overview
- Step-by-step tutorials
- Screenshots/diagrams
- Common workflows
- FAQ

Style:
- Active voice
- Present tense
- Short paragraphs
- Bullet points for lists
- Code blocks with syntax highlighting
- Tables for reference data
```

---

## Tools and Capabilities

| Tool | Purpose |
|------|---------|
| `read_file` | Read generated code for examples |
| `write_file` | Write documentation files |
| `generate_diagram` | Create Mermaid diagrams |

---

## Success Criteria

✅ README complete with quickstart
✅ API documentation covers all endpoints
✅ Deployment guide step-by-step
✅ Architecture documented
✅ User guide with examples
✅ Troubleshooting section
✅ Known issues documented

---

## Output Example

### README.md Structure

```markdown
# Project Name

Brief description of what this project does.

## Features

- ✅ User authentication with JWT
- ✅ Todo CRUD operations
- ✅ RESTful API
- ✅ React frontend with TypeScript
- ✅ PostgreSQL database

## Tech Stack

**Frontend:**
- React 18
- TypeScript
- Tailwind CSS
- Vite

**Backend:**
- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 22+
- PostgreSQL 16+

### Installation

1. Clone repository:
```bash
git clone <repo-url>
cd project-name
```

2. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
```

### Configuration

Create `.env` file in backend directory:
```bash
DATABASE_URL=postgresql://user:pass@localhost/dbname
SECRET_KEY=your-secret-key
```

### Run Migrations

```bash
cd backend
alembic upgrade head
```

### Start Development Servers

Backend:
```bash
uvicorn backend.main:app --reload
```

Frontend:
```bash
cd frontend
npm run dev
```

### Access Application

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## API Documentation

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete API reference.

### Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login user |
| `/api/v1/todos` | GET | Get all todos |
| `/api/v1/todos` | POST | Create todo |
| `/api/v1/todos/{id}` | PUT | Update todo |
| `/api/v1/todos/{id}` | DELETE | Delete todo |

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

## Testing

Backend:
```bash
pytest backend/tests/
```

Frontend:
```bash
npm run test
```

Coverage:
```bash
pytest --cov=backend backend/tests/
```

## Known Issues

- Todo text limited to 500 characters (see issue #1)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md)

## License

MIT
```

---

**Document Version:** 1.0
**Agent ID:** docs_001
**Last Updated:** 2026-02-13
