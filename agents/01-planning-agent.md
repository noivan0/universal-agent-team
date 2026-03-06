# Planning Agent Specification

## Overview

The Planning Agent is the first agent in the multi-agent workflow. It analyzes user requirements, breaks them down into actionable tasks, identifies dependencies, and creates a comprehensive project plan. This agent serves as the foundation for all subsequent agents by establishing clear requirements and execution strategy.

## Role and Responsibilities

### Primary Responsibility
Analyze user requirements and create a detailed, actionable project plan with task breakdown and dependency identification.

### Secondary Responsibilities
- Extract key features and functional requirements from user input
- Identify project risks and ambiguities
- Assess project complexity and scope
- Create initial task estimates
- Flag requirements that need clarification

### What This Agent Does NOT Do
- ❌ Design system architecture (Architecture Agent's role)
- ❌ Make technology stack decisions (Architecture Agent's role)
- ❌ Write code or generate implementations
- ❌ Create detailed technical specifications
- ❌ Perform project management or tracking (after planning phase)

---

## Input Requirements

### Required Inputs

From `AgentState`:

| Field | Type | Description |
|-------|------|-------------|
| `user_request` | `str` | User's project description or requirements |

**Minimum Requirements:**
- `user_request` must be non-empty string
- Length >= 10 characters (meaningful request)

### Optional Inputs

| Field | Type | Description |
|-------|------|-------------|
| `project_context` | `dict[str, Any]` | Additional context (constraints, preferences, existing code) |

**Optional Context Fields:**
```python
{
    "tech_stack": list[str],           # Preferred technologies
    "constraints": list[str],          # Budget, timeline, team size
    "existing_codebase": str,          # Path to existing code
    "target_users": str,               # User persona
    "deployment_target": str           # Cloud provider, on-prem, etc.
}
```

### Validation Rules

```python
def validate_input(self, state: AgentState) -> bool:
    """
    Validate that state contains valid user request.

    Returns:
        True if user_request is non-empty and meaningful
    """
    if not state.user_request:
        return False

    if len(state.user_request.strip()) < 10:
        self.logger.warning("User request too short to analyze")
        return False

    return True
```

---

## Output Specifications

### Primary Outputs

The Planning Agent returns a dictionary with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `requirements` | `str` | Full requirements document (markdown format) |
| `tasks` | `list[TaskStatus]` | Actionable task breakdown |
| `current_phase` | `str` | Set to `"design"` |
| `next_agent` | `str` | Set to `"architecture"` |
| `message` | `str` | Summary of planning work |

### Artifacts

The Planning Agent produces artifacts for downstream agents:

```python
artifacts = {
    "requirements": str,              # Detailed requirements document
    "tasks": list[TaskStatus],        # Task objects
    "dependencies": dict[str, list],  # Task dependency graph
    "risks": list[str],               # Identified risks/ambiguities
    "features": list[dict],           # Feature breakdown
    "user_stories": list[str]         # User stories (if applicable)
}
```

**Example TaskStatus:**
```python
TaskStatus(
    task_id="task_001",
    description="Design database schema for user authentication",
    assigned_to="architecture",
    status="pending",
    dependencies=[],  # No dependencies
    complexity="medium"
)
```

**Example Dependency Graph:**
```python
{
    "task_001": [],                    # No dependencies
    "task_002": ["task_001"],          # Depends on task_001
    "task_003": ["task_001", "task_002"]  # Depends on both
}
```

### State Updates

Fields modified in `AgentState`:

```python
{
    "requirements": "<generated requirements doc>",
    "tasks": [TaskStatus(...), TaskStatus(...), ...],
    "messages": [..., AgentMessage(agent_id="planning_001", ...)],
    "current_phase": "design",
    "next_agent": "architecture",
    "is_complete": False
}
```

---

## LLM Configuration

### Model

```python
{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.3,
    "max_tokens": 4096,
    "timeout": 120
}
```

### Rationale

- **Low temperature (0.3)**: Planning requires precision and consistency
- **Claude 3.5 Sonnet**: Excellent at structured analysis and task breakdown
- **4096 tokens**: Sufficient for detailed requirements and task lists
- **120s timeout**: Requirements analysis typically completes quickly

---

## System Prompt

```
You are a senior project planning specialist and requirements analyst.

Your responsibilities:
1. Analyze user requirements and extract key features
2. Break down projects into discrete, actionable tasks
3. Identify dependencies between tasks
4. Estimate complexity and suggest task ordering
5. Flag potential risks, ambiguities, or missing information

Analysis Guidelines:
- Be specific: "Implement user authentication" → "Create user registration endpoint with email/password validation"
- Identify dependencies: Task B cannot start until Task A completes
- Assess complexity: Consider team size, timeline, technical challenges
- Flag ambiguities: Missing information that needs clarification
- Think holistically: Consider frontend, backend, database, deployment, testing

Output Requirements:
1. Detailed requirements document (markdown format)
2. Task list with clear descriptions
3. Dependency graph showing task relationships
4. Risk assessment highlighting potential issues
5. Recommended execution order

Task Breakdown Principles:
- Each task should be completable by a single agent
- Tasks should be specific and measurable
- Tasks should have clear acceptance criteria
- Avoid overly granular tasks (too many small tasks)
- Avoid overly broad tasks (impossible to complete in one step)

Example Good Task:
- "Design and implement REST API for user authentication with JWT tokens"
- Clear scope, specific technology, measurable outcome

Example Bad Task:
- "Build the backend" (too broad)
- "Add semicolon to line 47" (too granular)

Remember: Your analysis is the foundation for all subsequent agents. Be thorough and precise.
```

---

## Tools and Capabilities

### Available Tools

The Planning Agent uses **no external tools**. It performs pure analysis using the LLM.

### Permissions

- ✅ Read: `user_request`, `project_context`
- ✅ Write: `requirements`, `tasks`, `messages`
- ❌ File system access: Not required
- ❌ Code execution: Not required
- ❌ External API calls: Not required

---

## Workflow Integration

### Prerequisites

**Must be completed before Planning Agent runs:**
- User has provided a project request
- Initial `AgentState` has been created

**State Requirements:**
```python
AgentState(
    user_request="<user's project description>",
    project_context={...}  # Optional
)
```

### Triggers

The Planning Agent is triggered when:
1. Workflow starts (entry point)
2. User submits a new project request
3. Requirements need to be re-analyzed after major changes

**Orchestrator Configuration:**
```python
# Planning Agent is the entry point
workflow.set_entry_point("planning")
```

### Next Steps

After the Planning Agent completes:

**Success Path:**
```
Planning Agent
     ↓
Architecture Agent (next_agent = "architecture")
```

**Error Path:**
```
Planning Agent (validation failed)
     ↓
Human Review (requires_human_approval = True)
```

**Orchestrator Routing:**
```python
def router(state: AgentState) -> str:
    if state.requires_human_approval:
        return "human_review"

    if state.current_phase == "planning":
        return "architecture"

    # ... other routing logic
```

---

## Success Criteria

### Measurable Criteria for Successful Execution

✅ **Requirements Completeness**
- All major features extracted from user request
- User stories defined (if applicable)
- Functional requirements clearly stated
- Non-functional requirements identified (if mentioned)

✅ **Task Quality**
- Minimum 3 tasks created (for non-trivial projects)
- Each task has clear description
- Each task assigned to appropriate agent
- No duplicate or overlapping tasks

✅ **Dependency Accuracy**
- Dependencies correctly identified
- No circular dependencies
- Dependency graph is valid (topological sort possible)

✅ **Risk Identification**
- Ambiguities flagged
- Technical risks noted
- Missing information identified

✅ **State Updates**
- `requirements` field populated
- `tasks` list contains TaskStatus objects
- `next_agent` set to "architecture"
- `current_phase` set to "design"
- `message` summarizes work performed

### Validation Checks

```python
def validate_output(output: dict) -> bool:
    """Validate Planning Agent output."""
    # Check required fields
    assert "requirements" in output
    assert "tasks" in output
    assert "next_agent" in output
    assert output["next_agent"] == "architecture"

    # Check task quality
    assert len(output["tasks"]) >= 3
    for task in output["tasks"]:
        assert task.description
        assert task.assigned_to
        assert task.status == "pending"

    # Check for circular dependencies
    dependencies = output.get("artifacts", {}).get("dependencies", {})
    assert is_acyclic(dependencies)

    return True
```

---

## Error Handling

### Common Errors

#### Error 1: Empty or Invalid User Request

**Cause:**
- User provided empty string
- User request too short to be meaningful
- User request is gibberish or non-sensical

**Resolution:**
```python
if not self.validate_input(state):
    return {
        "errors": ["Planning Agent: Invalid user request"],
        "message": "Cannot analyze empty or invalid request",
        "requires_human_approval": True
    }
```

#### Error 2: LLM Parsing Failure

**Cause:**
- LLM output does not match expected format
- Cannot extract structured task list from response

**Resolution:**
```python
try:
    tasks = self._parse_tasks(llm_response.content)
except ValueError as e:
    self.logger.error(f"Failed to parse LLM response: {e}")
    return {
        "errors": [f"Planning Agent: Parse error - {str(e)}"],
        "retry_count": state.retry_count + 1
    }
```

#### Error 3: Ambiguous Requirements

**Cause:**
- User request is too vague
- Missing critical information
- Multiple conflicting interpretations possible

**Resolution:**
```python
# Flag for human clarification
if self._detect_ambiguity(requirements):
    return {
        "requirements": requirements,
        "tasks": [],  # Cannot create tasks yet
        "message": "Requirements are ambiguous, need clarification",
        "requires_human_approval": True,
        "artifacts": {
            "clarification_needed": [
                "What authentication method should be used?",
                "What database is preferred?",
                # ...
            ]
        }
    }
```

#### Error 4: LLM Timeout

**Cause:**
- Complex project taking too long to analyze
- LLM API slow response

**Resolution:**
- Retry with exponential backoff
- If retries exhausted, escalate to human review

### Retry Strategy

```python
class PlanningAgent(BaseAgent):
    def execute(self, state: AgentState) -> AgentState:
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Validate input
                if not self.validate_input(state):
                    raise ValueError("Invalid input state")

                # Process
                result = self.process(state)

                # Update state and return
                state.messages.append(AgentMessage(...))
                for key, value in result.items():
                    if hasattr(state, key):
                        setattr(state, key, value)

                return state

            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")

                if attempt == max_retries - 1:
                    # Final retry failed
                    state.errors.append(f"Planning Agent: {str(e)}")
                    state.retry_count += 1
                    state.requires_human_approval = True
                    return state

                # Exponential backoff
                time.sleep(2 ** attempt)

        return state
```

---

## Examples

### Example 1: Simple Todo App

**Input:**
```python
AgentState(
    user_request="Build a todo list web application with user authentication",
    project_context={}
)
```

**Process:**
1. Analyze request: Todo app + authentication
2. Extract features: User registration, login, todo CRUD
3. Break down into tasks
4. Identify dependencies

**Output:**
```python
{
    "requirements": """
# Todo List Application - Requirements

## Overview
A web-based todo list application with user authentication.

## Functional Requirements
1. User Authentication
   - User registration with email/password
   - User login with JWT tokens
   - Password hashing and security

2. Todo Management
   - Create new todo items
   - Read/list all todos for logged-in user
   - Update todo (mark complete, edit text)
   - Delete todo items

3. Data Persistence
   - Store users and todos in database
   - Associate todos with user accounts

## Non-Functional Requirements
- Secure authentication (no plaintext passwords)
- Responsive UI (works on mobile and desktop)
- Fast response times (< 200ms for API calls)

## Technical Stack (suggested)
- Frontend: React + TypeScript
- Backend: Python FastAPI
- Database: PostgreSQL
- Authentication: JWT tokens
""",

    "tasks": [
        TaskStatus(
            task_id="task_001",
            description="Design database schema for users and todos",
            assigned_to="architecture",
            status="pending",
            complexity="low"
        ),
        TaskStatus(
            task_id="task_002",
            description="Design REST API endpoints for auth and todo CRUD",
            assigned_to="architecture",
            status="pending",
            complexity="medium"
        ),
        TaskStatus(
            task_id="task_003",
            description="Implement user registration and login API with JWT",
            assigned_to="backend",
            status="pending",
            complexity="medium",
            dependencies=["task_002"]
        ),
        TaskStatus(
            task_id="task_004",
            description="Implement todo CRUD API endpoints",
            assigned_to="backend",
            status="pending",
            complexity="low",
            dependencies=["task_002", "task_003"]
        ),
        TaskStatus(
            task_id="task_005",
            description="Create React components for login/register forms",
            assigned_to="frontend",
            status="pending",
            complexity="low",
            dependencies=["task_002"]
        ),
        TaskStatus(
            task_id="task_006",
            description="Create React todo list component with CRUD",
            assigned_to="frontend",
            status="pending",
            complexity="medium",
            dependencies=["task_005"]
        ),
        TaskStatus(
            task_id="task_007",
            description="Write unit and integration tests",
            assigned_to="qa",
            status="pending",
            complexity="medium",
            dependencies=["task_003", "task_004", "task_005", "task_006"]
        ),
        TaskStatus(
            task_id="task_008",
            description="Generate API documentation and README",
            assigned_to="documentation",
            status="pending",
            complexity="low",
            dependencies=["task_007"]
        )
    ],

    "artifacts": {
        "dependencies": {
            "task_001": [],
            "task_002": ["task_001"],
            "task_003": ["task_002"],
            "task_004": ["task_002", "task_003"],
            "task_005": ["task_002"],
            "task_006": ["task_005"],
            "task_007": ["task_003", "task_004", "task_005", "task_006"],
            "task_008": ["task_007"]
        },
        "risks": [
            "No specific authentication method mentioned (JWT assumed)",
            "Database choice not specified (PostgreSQL suggested)",
            "No mention of deployment requirements"
        ],
        "features": [
            {
                "name": "User Authentication",
                "priority": "high",
                "complexity": "medium"
            },
            {
                "name": "Todo CRUD",
                "priority": "high",
                "complexity": "low"
            }
        ]
    },

    "current_phase": "design",
    "next_agent": "architecture",
    "message": "Created 8 tasks for todo application with authentication"
}
```

---

### Example 2: Ambiguous Request Requiring Clarification

**Input:**
```python
AgentState(
    user_request="Build a chat app",
    project_context={}
)
```

**Process:**
1. Analyze request: Too vague
2. Identify missing information
3. Generate clarification questions
4. Flag for human review

**Output:**
```python
{
    "requirements": """
# Chat Application - Requirements (INCOMPLETE)

## User Request
"Build a chat app"

## Ambiguities Requiring Clarification

### Critical Questions
1. **Type of chat:**
   - One-on-one messaging?
   - Group chat rooms?
   - Public channels?
   - All of the above?

2. **Real-time communication:**
   - Should messages appear instantly?
   - Technology: WebSockets, polling, or other?

3. **User authentication:**
   - Email/password login?
   - OAuth (Google, GitHub, etc.)?
   - Anonymous users allowed?

4. **Message persistence:**
   - Store message history?
   - How long to keep messages?

5. **Additional features:**
   - File sharing?
   - Voice/video calls?
   - Typing indicators?
   - Read receipts?

### Assumptions (if no clarification provided)
- One-on-one messaging
- Real-time with WebSockets
- Email/password authentication
- Basic text messages only
- Persistent message history
""",

    "tasks": [],  # Cannot create tasks without clarification

    "artifacts": {
        "clarification_needed": [
            "What type of chat (1-on-1, group, channels)?",
            "Real-time required? If so, WebSockets or polling?",
            "Authentication method (email/password, OAuth, anonymous)?",
            "Should messages be persisted? For how long?",
            "Any additional features (files, voice, video, typing indicators)?"
        ]
    },

    "message": "Requirements are too ambiguous, flagging for clarification",
    "requires_human_approval": True,
    "next_agent": None  # Wait for human input
}
```

---

## Integration Example

**Full workflow integration:**

```python
from backend.agents.planning_agent import PlanningAgent
from backend.orchestrator.state import AgentState
from backend.core.llm import get_llm

# Initialize agent
llm = get_llm(provider="anthropic", model="claude-3-5-sonnet-20241022")
planning_agent = PlanningAgent(
    agent_id="planning_001",
    role="planning",
    llm=llm
)

# Create initial state
initial_state = AgentState(
    user_request="Build a todo list app with user authentication",
    project_context={"tech_stack": ["React", "FastAPI"]}
)

# Execute planning agent
result_state = planning_agent.execute(initial_state)

# Check result
if result_state.requires_human_approval:
    print("⚠️  Needs human review")
    print(f"Clarifications: {result_state.messages[-1].artifacts.get('clarification_needed')}")
else:
    print("✅ Planning complete")
    print(f"Created {len(result_state.tasks)} tasks")
    print(f"Next agent: {result_state.next_agent}")

# Pass to next agent
if result_state.next_agent == "architecture":
    # Continue to architecture agent
    architecture_state = architecture_agent.execute(result_state)
```

---

## Metrics & Monitoring

**Key Metrics to Track:**

```python
{
    "agent_id": "planning_001",
    "execution_time_ms": 2500,
    "success": True,
    "tasks_created": 8,
    "risks_identified": 3,
    "retry_count": 0,
    "llm_tokens_used": 1250,
    "timestamp": "2026-02-13T10:30:00Z"
}
```

**Alerts:**
- Execution time > 60s (may need prompt optimization)
- Success rate < 95% (investigate input validation or LLM issues)
- Average tasks_created < 3 (may not be breaking down properly)

---

**Document Version:** 1.0
**Agent ID:** planning_001
**Last Updated:** 2026-02-13
