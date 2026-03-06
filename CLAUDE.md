# CLAUDE.md - Multi-Agent AI Development System

## Table of Contents
1. [Quick Start with Claude Code](#quick-start-with-claude-code)
2. [System Overview](#system-overview)
3. [Development Guidelines](#development-guidelines)
4. [Agent Interaction Protocols](#agent-interaction-protocols)
5. [Architecture & Design Principles](#architecture--design-principles)
6. [Workflow Rules](#workflow-rules)
7. [Deployment & Operations](#deployment--operations)
8. [Troubleshooting](#troubleshooting)

---

## 1. Quick Start with Claude Code

### The Simplest Way: Just Talk to Claude Code!

Claude Code can orchestrate the entire multi-agent workflow **without any code**. Just describe what you want to build:

**Example Conversation:**

```
You: "Build a todo list application with user authentication using React and FastAPI"

Claude Code: I'll orchestrate the multi-agent system to build this for you.

[Automatically executes:]
1. Planning Agent - analyzes requirements
2. Architecture Agent - designs system
3. Frontend Agent (parallel) - generates React components
4. Backend Agent (parallel) - generates FastAPI code
5. QA Agent - runs tests
6. Documentation Agent - creates docs

Result: Complete todo app in /workspace/generated/
```

### How It Works

1. **You provide a request** - Describe your project in natural language
2. **Claude Code orchestrates** - Automatically routes between specialized agents
3. **Agents execute in parallel** - Frontend and Backend run simultaneously via Task tool
4. **State saved as JSON** - Simple checkpoint files you can inspect
5. **Output delivered** - Generated code, tests, and docs ready to use


**What Claude Code does automatically:**

```
📋 Planning Agent
   ↓ Creates: requirements.md, task breakdown

🏗️ Architecture Agent
   ↓ Creates: system_design.md, API specs, DB schema

🔀 PARALLEL EXECUTION (via multiple Task calls)
   ├─ 🎨 Frontend Agent → React admin panel
   └─ ⚙️ Backend Agent → FastAPI endpoints

✅ QA Agent
   ↓ Runs: pytest, coverage reports

📚 Documentation Agent
   ↓ Generates: README, API docs, deployment guide

✨ Done! Your blog API is ready.
```

### Advantages Over Traditional Orchestration

| Feature | Claude Code Native | Traditional (LangGraph) |
|---------|-------------------|------------------------|
| **Setup time** | 0 seconds | Hours (install Redis, configure graph) |
| **Configuration** | None | Complex graph definition |
| **Parallel execution** | Automatic (multiple Tasks) | Manual edge configuration |
| **Debugging** | Read JSON files | Query Redis/PostgreSQL |
| **Iteration speed** | Instant | Restart services |
| **Cost** | No infrastructure | Redis + PostgreSQL hosting |


---

## 2. System Overview

### Purpose
This multi-agent system orchestrates 6 specialized AI agents to collaboratively build software projects from requirements to deployment.

**Two orchestration modes available:**
- **Claude Code Native** (Recommended): Zero-config orchestration using Claude's Task tool
- **LangGraph** (Optional): Traditional graph-based orchestration for production scale

### Agents

| Agent | Role | Responsibility |
|-------|------|----------------|
| **Planning Agent** | Requirements Analyst | Analyzes user requirements, creates task breakdown, identifies dependencies |
| **Architecture Design Agent** | System Architect | Designs system architecture, defines component specs, creates API contracts |
| **Frontend Development Agent** | UI Developer | Implements React/TypeScript components, integrates with backend APIs |
| **Backend Development Agent** | API Developer | Implements Python/FastAPI endpoints, business logic, database schemas |
| **Backtesting & QA Agent** | Quality Assurance | Runs tests, validates code quality, generates coverage reports |
| **Documentation Agent** | Technical Writer | Generates comprehensive documentation from all project artifacts |

### Technology Stack

**Orchestration:**
- **Claude Code Native** - Lightweight orchestration using Claude's Task tool (Recommended for prototypes)
- LangGraph 0.2.x - Graph-based multi-agent state management (Optional for production scale)
- Pydantic 2.x - Type-safe state models
- File-based checkpointing (JSON/YAML) - Simple state persistence

**Backend:**
- Python 3.12 (managed by uv)
- FastAPI - REST API framework
- PostgreSQL - Persistent storage (Optional)
- Redis - State checkpointing (Optional for LangGraph mode)
- Anthropic Python SDK - Claude API

**Frontend:**
- React 18+ with TypeScript
- Vite - Build tool
- TanStack Query - Server state management
- Zustand - Client state management
- Tailwind CSS + Shadcn/ui

**Infrastructure:**
- Docker + Docker Compose
- CUDA 12.4.1 (GPU support)
- Node.js 22
- PyTorch

---

## 2. Development Guidelines

### Code Standards

#### Python (PEP 8 + Ruff)

**Formatting:**
- Line length: 100 characters
- Use Ruff for linting and formatting
- Python 3.12+ features encouraged

**Type Hints:**
- Required for all function signatures
- Use `typing` module for complex types
- Prefer `list[T]` and `dict[K, V]` over `List[T]` and `Dict[K, V]` (Python 3.12+)

**Docstrings:**
- Google style for all public functions and classes
- Include Args, Returns, Raises sections

**Naming Conventions:**
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- Private members prefixed with `_`

**Imports:**
- Absolute imports preferred
- Grouped: stdlib, third-party, local
- Sorted alphabetically within groups

**Example:**
```python
from typing import Optional
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """Configuration for an AI agent.

    Attributes:
        agent_id: Unique identifier for the agent
        role: Agent's primary responsibility
        max_retries: Maximum retry attempts on failure
    """
    agent_id: str
    role: str
    max_retries: int = 3

    def validate_config(self) -> bool:
        """Validate configuration parameters.

        Returns:
            True if configuration is valid, False otherwise

        Raises:
            ValueError: If agent_id is empty
        """
        if not self.agent_id:
            raise ValueError("agent_id cannot be empty")
        return True
```

#### TypeScript/React

**Formatting:**
- ESLint + Prettier
- 2-space indentation
- Semicolons required
- Single quotes for strings

**Types:**
- Strict TypeScript mode enabled
- No `any` types (use `unknown` if necessary)
- Explicit return types for functions

**Components:**
- Functional components only
- TypeScript interfaces for props
- Props destructuring in parameter list

**Naming Conventions:**
- `PascalCase` for components and types
- `camelCase` for functions, variables, hooks
- Custom hooks prefixed with `use`

**Example:**
```typescript
interface AgentStatusProps {
  agentId: string;
  status: 'idle' | 'running' | 'error';
  onStatusChange?: (newStatus: string) => void;
}

export const AgentStatus: React.FC<AgentStatusProps> = ({
  agentId,
  status,
  onStatusChange
}) => {
  const [loading, setLoading] = useState<boolean>(false);

  const handleStatusUpdate = (newStatus: string): void => {
    setLoading(true);
    onStatusChange?.(newStatus);
    setLoading(false);
  };

  return (
    <div className="agent-status">
      <span>{agentId}: {status}</span>
    </div>
  );
};
```

### Testing Requirements

**Coverage:**
- Minimum 80% code coverage
- 100% coverage for critical paths (state management, routing, agent execution)

**Test Types:**
- **Unit tests**: Test individual agent methods and utilities
- **Integration tests**: Test agent-to-agent communication via state
- **End-to-end tests**: Test complete workflows (Planning → Architecture → ... → Docs)

**Test Organization:**
```python
# Good test structure
def test_planning_agent_validates_empty_request():
    """Planning agent should reject empty user requests."""
    agent = PlanningAgent(...)
    state = AgentState(user_request="")

    assert not agent.validate_input(state)

def test_planning_agent_creates_tasks():
    """Planning agent should create actionable tasks from requirements."""
    agent = PlanningAgent(...)
    state = AgentState(user_request="Build a todo app")

    result = agent.process(state)

    assert "tasks" in result
    assert len(result["tasks"]) > 0
    assert result["next_agent"] == "architecture"
```

### Git Workflow

**Branches:**
- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - Feature branches
- `bugfix/*` - Bug fixes

**Commits:**
- Use conventional commits: `type(scope): message`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Examples:
  - `feat(planning-agent): add dependency detection`
  - `fix(orchestrator): handle concurrent state updates`
  - `docs(claude-md): update agent interaction protocols`

**Pull Requests:**
- Descriptive title and summary
- Link to related issues
- All tests passing
- Code review required

---

## 3. Agent Interaction Protocols

### Communication Model

Agents communicate through **shared state** that can be managed in two ways:

**Option 1: Claude Code Native (File-Based)**
- State stored as JSON/YAML checkpoint files
- Claude Code reads/writes state files between agent executions
- Simple `state.json` file in `/workspace/checkpoints/`
- Easy to inspect and debug

**Option 2: LangGraph (Database-Based)**
- State managed by LangGraph orchestrator
- Redis or PostgreSQL for persistence
- More robust for production environments

**Key Principles (Both Modes):**
1. **Immutable state updates**: Agents return state updates; orchestrator applies them
2. **Type safety**: All state defined with Pydantic models
3. **Explicit contracts**: Clear input/output specifications per agent
4. **No side effects**: Agents don't modify external systems during state transitions

### State Contract

All agents MUST follow this contract:

**Input Validation:**
```python
def validate_input(self, state: AgentState) -> bool:
    """
    Check if state contains all required inputs for this agent.

    Returns:
        True if state is valid, False otherwise
    """
    pass
```

**Processing:**
```python
def process(self, state: AgentState) -> dict[str, Any]:
    """
    Execute agent logic and return state updates.

    Returns:
        Dictionary of state field updates
        MUST include: next_agent, message
        MAY include: artifacts, task updates, errors
    """
    pass
```

**Execution:**
```python
def execute(self, state: AgentState) -> AgentState:
    """
    Full execution with validation and error handling.
    Implemented in BaseAgent, do not override.
    """
    pass
```

### Message Format

Agents communicate via `AgentMessage` objects:

```python
class AgentMessage(BaseModel):
    agent_id: str                    # Unique agent identifier
    role: Literal[...]               # Agent role/type
    content: str                     # Human-readable summary
    artifacts: dict[str, Any]        # Structured data for other agents
    timestamp: datetime              # When message was created
```

**Example:**
```python
# Architecture Agent creates message for Frontend Agent
message = AgentMessage(
    agent_id="arch_001",
    role="architecture",
    content="Created 5 component specifications",
    artifacts={
        "component_specs": {
            "UserDashboard": {
                "type": "React.FC",
                "props": {
                    "userId": "string",
                    "onUpdate": "(data: any) => void"
                },
                "state": ["loading", "userData"],
                "api_calls": ["/api/users/{id}"]
            }
        }
    },
    timestamp=datetime.utcnow()
)
```

### Artifacts Schema

Artifacts are structured data passed between agents. Each agent type produces specific artifact schemas:

#### Planning Agent → Architecture Agent
```python
{
    "requirements": str,              # Full requirements document
    "tasks": list[TaskStatus],        # Task breakdown
    "dependencies": dict[str, list],  # Task dependency graph
    "risks": list[str]                # Identified risks
}
```

#### Architecture Agent → Development Agents
```python
{
    "system_design": {
        "architecture_pattern": str,
        "data_flow": dict,
        "component_diagram": str
    },
    "component_specs": {
        "<ComponentName>": {
            "type": str,
            "props": dict,
            "state": list[str],
            "api_calls": list[str]
        }
    },
    "api_specs": {
        "<endpoint>": {
            "method": str,
            "request_schema": dict,
            "response_schema": dict,
            "authentication": bool
        }
    }
}
```

#### Development Agents → QA Agent
```python
{
    "code_files": {
        "<file_path>": str  # File content
    },
    "dependencies": list[str],
    "test_requirements": list[str]
}
```

#### QA Agent → Documentation Agent
```python
{
    "test_results": {
        "total": int,
        "passed": int,
        "failed": int,
        "coverage_percent": float
    },
    "test_cases": list[dict],
    "bug_reports": list[dict]
}
```

### Handoff Protocol

When an agent completes its work, it MUST:

1. **Update artifacts** in message
2. **Set `next_agent`** field in state update
3. **Update `current_phase`** to next phase
4. **Mark tasks as completed** if applicable
5. **Add descriptive message** summarizing work done

**Example:**
```python
def process(self, state: AgentState) -> dict[str, Any]:
    # ... do work ...

    return {
        "architecture_doc": architecture_document,
        "artifacts": {...},  # Structured data for next agent
        "next_agent": "frontend",
        "current_phase": "frontend",
        "message": "Architecture design complete. Created 5 components, 12 API endpoints.",
        "tasks": updated_tasks  # Mark architecture tasks as completed
    }
```

### Error Communication

Agents communicate errors through state:

```python
# In agent's process() method
try:
    result = do_work()
except Exception as e:
    return {
        "errors": [f"{self.role}: {str(e)}"],
        "retry_count": state.retry_count + 1,
        "message": f"Error during {self.role}: {str(e)}"
    }
```

---

## 4. Architecture & Design Principles

### System Architecture

**Two Orchestration Modes:**

#### Mode 1: Claude Code Native (Recommended for Prototypes)

**Pattern:** Dynamic Task-Based Orchestration

```
              ┌─────────────────────────┐
              │   Claude Code (You!)    │
              │  Dynamic Orchestrator   │
              └────────────┬────────────┘
                           │
          ┌────────────────┼────────────────┐
          │ (Task tool)    │ (Task tool)    │ (Parallel execution)
          ▼                ▼                ▼
  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
  │Planning Agent│  │Arch Agent │  │Frontend Agent│
  └──────────────┘  └──────────┘  └──────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
              ┌─────────────────────────┐
              │ AgentState (JSON file)  │
              │   /workspace/state.json │
              └─────────────────────────┘
```

**Components:**
- **Claude Code**: Directly orchestrates agents using Task tool
- **Agents**: Simple Python functions returning state updates
- **State**: JSON/YAML checkpoint files
- **No external dependencies**: Just Pydantic for validation

**Advantages:**
- ✅ Zero orchestration framework overhead
- ✅ Native parallel execution via multiple Task calls
- ✅ Dynamic routing based on Claude's reasoning
- ✅ Simple file-based state (easy debugging)
- ✅ Fast prototyping and iteration

#### Mode 2: LangGraph (Optional for Production Scale)

**Pattern:** Hierarchical Orchestrator (Hub-and-Spoke)

```
              ┌─────────────────────────┐
              │  LangGraph Orchestrator │
              │    (Central Router)     │
              └────────────┬────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
  │Planning Agent│  │Arch Agent │  │Frontend Agent│
  └──────────────┘  └──────────┘  └──────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
              ┌─────────────────────────┐
              │    AgentState (Redis)   │
              │   (Pydantic BaseModel)  │
              └─────────────────────────┘
```

**Components:**
- **LangGraph Orchestrator**: Pre-configured graph routing
- **Agents**: Graph nodes with state transformations
- **State**: Redis/PostgreSQL checkpointing
- **Requires**: LangGraph, LangChain, Redis dependencies

**Advantages:**
- ✅ Visual workflow diagrams (Mermaid)
- ✅ Robust state persistence and recovery
- ✅ Battle-tested for production workloads
- ✅ Built-in streaming and callbacks

### Choosing an Orchestration Mode

| Feature | Claude Code Native | LangGraph |
|---------|-------------------|-----------|
| **Setup Complexity** | Low (no dependencies) | High (Redis, LangGraph) |
| **Parallel Execution** | Native (multiple Tasks) | Manual configuration |
| **State Management** | File-based (JSON) | Database (Redis/PG) |
| **Debugging** | Easy (read JSON files) | Complex (inspect DB) |
| **Production Scale** | Small-medium projects | Large-scale deployments |
| **Dynamic Routing** | Built-in (Claude reasons) | Static graph definition |
| **Best For** | Prototypes, MVPs, iteration | Production, compliance |

### Design Principles

#### 1. Single Responsibility
Each agent has ONE primary function:
- Planning: Analyze requirements
- Architecture: Design system
- Frontend: Generate UI code
- Backend: Generate API code
- QA: Test and validate
- Documentation: Generate docs

**Anti-pattern:**
```python
# BAD: Planning agent doing architecture work
class PlanningAgent:
    def process(self, state):
        requirements = analyze_requirements()
        architecture = design_system()  # ❌ Not planning agent's job
```

#### 2. Type Safety
All state and messages use Pydantic models:

```python
# Good: Type-safe state
class AgentState(BaseModel):
    user_request: str
    messages: list[AgentMessage]
    current_phase: Literal["planning", "design", "frontend", ...]
```

#### 3. Idempotency
Agent operations should be repeatable with same result:

```python
# Good: Idempotent processing
def process(self, state: AgentState) -> dict[str, Any]:
    # Same input state always produces same output
    requirements = parse_requirements(state.user_request)
    return {"requirements": requirements}
```

#### 4. Observability
Comprehensive logging at every step:

```python
def execute(self, state: AgentState) -> AgentState:
    self.logger.info(f"Starting {self.role} agent")
    self.logger.debug(f"Input state: {state.model_dump()}")

    result = self.process(state)

    self.logger.info(f"Completed {self.role} agent")
    self.logger.debug(f"Output: {result}")
```

#### 5. Fault Tolerance
Graceful degradation and recovery:

```python
# Good: Retry with exponential backoff
for attempt in range(max_retries):
    try:
        result = agent.process(state)
        break
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        time.sleep(2 ** attempt)
```

### Data Flow

**Linear Workflow:**
```
User Request
    ↓
Planning Agent → requirements, tasks
    ↓
Architecture Agent → system design, component specs
    ↓
Frontend Agent → React/TS code
    ↓
Backend Agent → Python/FastAPI code
    ↓
QA Agent → test results, bugs
    ↓
Documentation Agent → final docs
    ↓
Complete
```

**Parallel Workflow (Claude Code Native):**
```
User Request → Planning → Architecture
                             ↓
                    ┌────────┴────────┐
                    ▼                 ▼
                Frontend          Backend    ← Executed in parallel via multiple Task calls
                    │                 │
                    └────────┬────────┘
                             ▼
                          QA Agent
                             ↓
                    Documentation
                             ↓
                         Complete
```

**How Claude Code Enables Parallel Execution:**
```python
# In a single Claude Code response, make multiple Task calls:
# Task 1: Frontend Agent
# Task 2: Backend Agent
# Both execute simultaneously, results merged into state
```

**Parallel Execution Example:**
When Claude Code orchestrates agents, it can invoke multiple agents in one response:

1. **Read current state** from `/workspace/checkpoints/state.json`
2. **Invoke parallel Tasks** in a single message:
   - Task(subagent_type="frontend", prompt="Generate React components...")
   - Task(subagent_type="backend", prompt="Generate FastAPI endpoints...")
3. **Merge results** from both agents into state
4. **Save checkpoint** with combined updates
5. **Continue to next phase** (QA Agent)

### File Organization

**Claude Code Native Mode:**
```
/workspace/
  agents/                    # Agent specifications (markdown)
    01-planning-agent.md
    02-architecture-agent.md
    03-frontend-agent.md
    04-backend-agent.md
    05-backtesting-qa-agent.md
    06-documentation-agent.md

  checkpoints/              # State persistence
    workflow_<id>_state.json
    workflow_<id>_state.yaml

  generated/                # Agent outputs
    frontend/               # Generated React code
    backend/                # Generated Python code
    docs/                   # Generated documentation

  CLAUDE.md                 # This file - orchestration guide
```

**LangGraph Mode (Optional):**
```
backend/
  agents/           # Agent implementations (one file per agent)
  orchestrator/     # LangGraph workflow, state, routing
  core/             # Shared utilities (config, LLM, tools)
  api/              # REST API endpoints
  db/               # Database models and repositories
  tests/            # All tests

frontend/
  components/       # React components
  hooks/            # Custom hooks
  services/         # API clients
  stores/           # State management
  types/            # TypeScript types
```

---

## 5. Workflow Rules

### Development Workflow

#### Phase 1: Planning
**Agent:** Planning Agent

**Input:**
- `user_request`: User's project description
- `project_context`: Optional additional context

**Process:**
1. Parse and analyze user request
2. Extract key features and requirements
3. Break down into actionable tasks
4. Identify task dependencies
5. Assess risks and ambiguities

**Output:**
- `requirements`: Detailed requirements document
- `tasks`: List of TaskStatus objects
- `dependencies`: Task dependency graph
- `risks`: List of identified risks

**Success Criteria:**
- All user requirements captured
- Tasks are specific and actionable
- Dependencies correctly identified
- Next agent set to "architecture"

**Next:** Architecture Design

---

#### Phase 2: Architecture Design
**Agent:** Architecture Design Agent

**Input:**
- `requirements`: From Planning Agent
- `tasks`: Task list

**Process:**
1. Design system architecture
2. Define component specifications
3. Create API contracts
4. Design database schema
5. Define data flow

**Output:**
- `architecture_doc`: Full architecture document
- `component_specs`: Frontend component specifications
- `api_specs`: Backend API specifications
- `database_schema`: Data model design

**Success Criteria:**
- Architecture is complete and implementable
- Component specs have clear interfaces
- API contracts are well-defined
- Next agent set to "frontend" or "backend"

**Next:** Frontend Development (can run in parallel with Backend)

---

#### Phase 3: Frontend Development
**Agent:** Frontend Development Agent

**Input:**
- `component_specs`: From Architecture Agent
- `api_specs`: API endpoints to integrate

**Process:**
1. Generate React components from specs
2. Create TypeScript types
3. Implement API integration
4. Add styling with Tailwind
5. Validate TypeScript compilation

**Output:**
- `frontend_code`: Dict of file_path → code
- `dependencies`: npm packages needed
- `test_requirements`: Component test specs

**Success Criteria:**
- All components implemented
- TypeScript compiles without errors
- API integration matches specs
- Next agent set to "qa"

**Next:** QA Agent

---

#### Phase 4: Backend Development
**Agent:** Backend Development Agent

**Input:**
- `api_specs`: From Architecture Agent
- `database_schema`: Data model

**Process:**
1. Generate FastAPI endpoints
2. Implement business logic
3. Create Pydantic models
4. Add database integration
5. Validate Python code with Ruff

**Output:**
- `backend_code`: Dict of file_path → code
- `dependencies`: pip packages needed
- `test_requirements`: API test specs

**Success Criteria:**
- All endpoints implemented
- Code passes Ruff validation
- Database models match schema
- Next agent set to "qa"

**Next:** QA Agent

---

#### Phase 5: Backtesting & QA
**Agent:** Backtesting & QA Agent

**Input:**
- `frontend_code`: From Frontend Agent
- `backend_code`: From Backend Agent
- `test_requirements`: Test specifications

**Process:**
1. Generate test cases
2. Run pytest for backend
3. Run Vitest for frontend
4. Calculate code coverage
5. Identify bugs and issues

**Output:**
- `test_results`: Test execution summary
- `coverage_report`: Coverage percentage
- `bug_reports`: List of issues found

**Success Criteria:**
- All tests executed
- Coverage > 80%
- Critical bugs identified
- Next agent set to "documentation" (if pass) or back to dev (if fail)

**Next:** Documentation Agent (if tests pass)

---

#### Phase 6: Documentation
**Agent:** Documentation Agent

**Input:**
- All artifacts from previous agents
- `frontend_code` and `backend_code`
- `test_results`

**Process:**
1. Generate README
2. Create API documentation
3. Write deployment guide
4. Document architecture
5. Create user guide

**Output:**
- `documentation`: Complete documentation package

**Success Criteria:**
- All sections complete
- Documentation accurate and comprehensive
- `is_complete` set to True

**Next:** END

---

### Error Handling Rules

#### 1. Retry Logic
- Maximum 3 retries per agent
- Exponential backoff: 2^n seconds
- Log each retry attempt
- After max retries, escalate to human review

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        result = agent.execute(state)
        break
    except Exception as e:
        logger.warning(f"Attempt {attempt + 1} failed: {e}")
        if attempt == max_retries - 1:
            state.requires_human_approval = True
            raise
        time.sleep(2 ** attempt)
```

#### 2. Validation Errors
- Fail fast with clear error message
- Do not retry validation errors
- Return error in state update

```python
if not self.validate_input(state):
    return {
        "errors": [f"{self.role}: Invalid input state"],
        "message": "Input validation failed",
        "next_agent": None  # Stop workflow
    }
```

#### 3. LLM Errors
- Timeout: 300 seconds
- Rate limit: Exponential backoff
- API error: Retry with fallback model
- Parse error: Re-prompt with structured output

#### 4. State Corruption
- Detect with Pydantic validation
- Rollback to last checkpoint
- Log corruption details
- Escalate to human review

### Human-in-the-Loop

Pause for human approval when:

1. **Major architectural decisions** - Multiple valid approaches exist
2. **Security-sensitive operations** - Credentials, permissions, etc.
3. **Test failures after max retries** - Cannot auto-fix
4. **Ambiguous requirements** - Clarification needed
5. **State corruption** - Cannot auto-recover

**Implementation (Claude Code Native):**
```python
# In state.json:
{
  "requires_human_approval": true,
  "current_phase": "planning",
  "errors": ["Requirements too ambiguous - need clarification"]
}

# Claude Code detects this flag and pauses workflow
# Uses AskUserQuestion tool to gather clarifications
```

**Implementation (LangGraph Mode):**
```python
def router(state: AgentState) -> str:
    if state.requires_human_approval:
        return "human_review"
    # ... normal routing
```

---

## 6. Deployment & Operations

### Environment Setup

**Prerequisites:**

**Claude Code Native Mode (Minimal):**
- Claude Code CLI installed
- Python 3.12+ with `pydantic` package
- Anthropic API key (for Claude)

**LangGraph Mode (Full Stack):**
- Docker and Docker Compose
- GPU with CUDA 12.4.1+ (optional for local LLM)
- Anthropic API key
- Redis and PostgreSQL

---

**Installation (Claude Code Native):**
```bash
# 1. Clone repository
git clone <repo-url>
cd multi-agent-system

# 2. Install minimal dependencies
pip install pydantic anthropic

# 3. Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# 4. Create checkpoint directory
mkdir -p /workspace/checkpoints

# 5. Start using Claude Code!
# Just talk to Claude Code and it will orchestrate agents automatically
```

**Installation (LangGraph Mode):**
```bash
# 1. Clone repository
git clone <repo-url>
cd multi-agent-system

# 2. Install Python dependencies with uv
uv sync

# 3. Install Node.js dependencies
cd frontend
npm install
cd ..

# 4. Create environment file
cp .env.example .env
# Edit .env and add:
#   ANTHROPIC_API_KEY=sk-ant-...
#   DATABASE_URL=postgresql://...
#   REDIS_URL=redis://localhost:6379

# 5. Start infrastructure services
docker-compose up -d redis postgres

# 6. Initialize database
python -m backend.db.init

# 7. Start backend
uvicorn backend.main:app --reload --port 8000

# 8. Start frontend (in separate terminal)
cd frontend
npm run dev
```

### Environment Variables

**Claude Code Native Mode:**

**Required:**
```bash
ANTHROPIC_API_KEY=sk-ant-...     # Claude API key
```

**Optional:**
```bash
CHECKPOINT_DIR=/workspace/checkpoints  # Where to save state files
MAX_AGENT_RETRIES=3                    # Retry attempts
LOG_LEVEL=INFO                         # Logging verbosity
```

**LangGraph Mode:**

**Required:**
```bash
ANTHROPIC_API_KEY=sk-ant-...     # Claude API key
DATABASE_URL=postgresql://...     # PostgreSQL connection string
REDIS_URL=redis://localhost:6379 # Redis connection string
```

**Optional:**
```bash
OPENAI_API_KEY=sk-...            # Fallback LLM
LOG_LEVEL=INFO                   # Logging verbosity
MAX_AGENT_RETRIES=3              # Retry attempts
AGENT_TIMEOUT=300                # Agent timeout (seconds)
ENABLE_HUMAN_REVIEW=true         # Human approval nodes
```

### Docker Deployment

**Production Stack:**
```yaml
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

  postgres:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Monitoring & Logging

**Logging:**
- Location: `/workspace/data/logs/`
- Format: Structured JSON
- Rotation: Daily
- Retention: 30 days

**Log Levels:**
- DEBUG: Detailed state transitions
- INFO: Agent start/complete
- WARNING: Retries, recoverable errors
- ERROR: Failures requiring attention

**Metrics:**
```python
# Track per-agent metrics
metrics = {
    "agent_id": str,
    "execution_time_ms": float,
    "success": bool,
    "retry_count": int,
    "timestamp": datetime
}
```

### Backup & Recovery

**Checkpoints:**
- Saved after each agent execution
- Location: Redis (development), PostgreSQL (production)
- Format: Serialized AgentState

**Recovery:**
```python
# Resume from checkpoint
checkpointer = RedisSaver(redis_url)
app = workflow.compile(checkpointer=checkpointer)

# Resume specific workflow
result = app.invoke(
    initial_state,
    config={"configurable": {"thread_id": "workflow_123"}}
)
```

---

## 7. Troubleshooting

### Common Issues

#### Agent Not Executing

**Symptoms:**
- Workflow stuck
- No logs from specific agent
- State not updating

**Causes & Solutions:**
1. **Input validation failing**
   - Check `validate_input()` implementation
   - Verify state has required fields
   - Add debug logging to validation

2. **Routing misconfigured**
   - Check `next_agent` field in state
   - Verify conditional edges in graph.py
   - Use `graph.draw_mermaid()` to visualize

3. **Exception silently caught**
   - Check error logging
   - Verify exception handling in `execute()`

---

#### LLM Timeouts

**Symptoms:**
- Agent execution exceeds 300s
- Timeout errors in logs

**Solutions:**
1. **Increase timeout:**
```python
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    timeout=600  # Increase to 10 minutes
)
```

2. **Reduce prompt complexity:**
- Break large tasks into smaller prompts
- Remove unnecessary context
- Use streaming for long responses

3. **Check API limits:**
- Verify API key is valid
- Check rate limits
- Monitor quota usage

---

#### State Corruption

**Symptoms:**
- Pydantic validation errors
- Missing required fields
- Type mismatches

**Solutions:**
1. **Check state updates:**
```python
# Ensure updates match AgentState schema
result = agent.process(state)
AgentState.model_validate(result)  # Will raise if invalid
```

2. **Restore from checkpoint:**
```python
# Get last valid checkpoint
checkpoint = checkpointer.get_latest(thread_id)
state = AgentState.model_validate(checkpoint["state"])
```

3. **Add validation to agents:**
```python
def process(self, state: AgentState) -> dict[str, Any]:
    updates = {...}

    # Validate before returning
    test_state = state.model_copy(update=updates)
    assert test_state.model_validate(test_state)

    return updates
```

---

#### Frontend-Backend Mismatch

**Symptoms:**
- API calls failing
- Type errors in frontend
- CORS errors

**Solutions:**
1. **Verify API schemas match:**
```python
# Backend (FastAPI)
class UserResponse(BaseModel):
    id: str
    name: str

# Frontend (TypeScript)
interface UserResponse {
  id: string;
  name: string;
}
```

2. **Check CORS configuration:**
```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)
```

3. **Verify proxy settings:**
```typescript
// frontend/vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

---

### Debug Mode

**Claude Code Native Mode:**

**Inspect current state:**
```bash
# Read the checkpoint file directly
cat /workspace/checkpoints/workflow_abc123_state.json | jq '.'

# Or use Python
python -c "
import json
with open('/workspace/checkpoints/workflow_abc123_state.json') as f:
    state = json.load(f)
    print(f\"Phase: {state['current_phase']}\")
    print(f\"Tasks: {len(state['tasks'])}\")
    print(f\"Errors: {state['errors']}\")
"
```

**View workflow history:**
```bash
# List all checkpoints
ls -lt /workspace/checkpoints/

# Compare state before/after agent execution
diff <(cat workflow_abc123_state.json | jq .) \
     <(cat workflow_abc123_state.json.backup | jq .)
```

**Enable verbose logging:**
```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

**LangGraph Mode:**

**Visualize workflow:**
```python
from langgraph.graph import Graph

# Generate Mermaid diagram
mermaid_diagram = graph.draw_mermaid()
print(mermaid_diagram)
```

**Inspect state at each step:**
```python
# Stream state transitions
for step in app.stream(initial_state):
    print(f"Current state: {step}")
    print(f"Current phase: {step.get('current_phase')}")
    print(f"Messages: {len(step.get('messages', []))}")
```

---

### Getting Help

**Claude Code Native Mode:**

1. **Check checkpoint files:**
```bash
cat /workspace/checkpoints/workflow_<id>_state.json | jq '.'
```

2. **View agent outputs:**
```bash
ls -R /workspace/generated/
```

3. **Ask Claude Code:**
```
"Show me the current workflow state"
"What phase are we in?"
"Are there any errors in the state?"
```

---

**LangGraph Mode:**

1. **Check logs:**
```bash
tail -f /workspace/data/logs/app_$(date +%Y%m%d).log
```

2. **Inspect Redis state:**
```bash
redis-cli
> KEYS langgraph:*
> GET langgraph:checkpoint:<thread_id>
```

3. **Review PostgreSQL artifacts:**
```sql
SELECT * FROM agent_artifacts ORDER BY created_at DESC LIMIT 10;
```

4. **LangGraph documentation:**
https://langchain-ai.github.io/langgraph/

5. **File an issue:**
Include: logs, state dump, LangGraph diagram, reproduction steps

---

## Appendix

### Quick Reference

**Agent Execution Order:**
```
Planning → Architecture → Frontend/Backend (parallel) → QA → Documentation
```

**State Fields:**
```python
user_request: str                    # Input
messages: list[AgentMessage]         # Agent communication
tasks: list[TaskStatus]              # Task tracking
current_phase: Literal[...]          # Workflow phase
requirements: Optional[str]          # Planning output
architecture_doc: Optional[str]      # Architecture output
frontend_code: dict[str, str]        # Frontend output
backend_code: dict[str, str]         # Backend output
test_results: Optional[dict]         # QA output
documentation: Optional[str]         # Docs output
next_agent: Optional[str]            # Routing
is_complete: bool                    # Workflow done
requires_human_approval: bool        # Pause for review
retry_count: int                     # Error handling
errors: list[str]                    # Error messages
```

**File Locations:**

**Claude Code Native Mode:**
```
/workspace/CLAUDE.md                # This file - orchestration guide
/workspace/agents/*.md              # Agent specifications
/workspace/checkpoints/*.json       # Workflow state files
/workspace/generated/               # Agent outputs
```

**LangGraph Mode:**
```
/workspace/CLAUDE.md                           # This file
/workspace/backend/orchestrator/state.py       # AgentState definition
/workspace/backend/orchestrator/graph.py       # LangGraph workflow
/workspace/backend/agents/base.py              # BaseAgent class
/workspace/backend/core/config.py              # Configuration
/workspace/agents/*.md                         # Agent specifications
```

**Useful Commands:**

**Claude Code Native Mode:**
```bash
# View current state
cat /workspace/checkpoints/workflow_*.json | jq '.'

# List all workflows
ls -lt /workspace/checkpoints/

# View generated code
tree /workspace/generated/

# Start Claude Code orchestration (just talk to Claude!)
# Example: "Build a todo app with React and FastAPI"
```

**LangGraph Mode:**
```bash
# Run tests
pytest backend/tests/

# Lint Python
ruff check backend/

# Lint TypeScript
cd frontend && npm run lint

# Type check
mypy backend/
cd frontend && npx tsc --noEmit

# Start all services
docker-compose up -d
uvicorn backend.main:app --reload &
cd frontend && npm run dev

# View logs
tail -f /workspace/data/logs/*.log

# Inspect LangGraph state
python -m backend.orchestrator.inspect_state <thread_id>
```

---

**Document Version:** 2.0 (Claude Code Native Edition)
**Last Updated:** 2026-02-13
**Maintained By:** Multi-Agent System Team

**Major Changes in v2.0:**
- ✨ Added Claude Code Native orchestration mode (zero dependencies)
- 🚀 Native parallel execution via Task tool
- 📁 File-based state management (no Redis/PostgreSQL required)
- 🎯 Simplified setup for prototypes and MVPs
- 📊 Comparison tables for choosing orchestration mode
- 💡 Quick Start guide with real examples
