# Agent Specifications

This directory contains detailed specifications for all agents in the Universal Agent Team system.

## Core Agents (6)

These agents form the foundation of the system and handle the complete development pipeline.

### 1. Planning Agent
**File**: [01-planning-agent.md](01-planning-agent.md)

**Role**: Requirements Analyst

**Responsibility**: Analyze user requirements and create actionable task breakdown

**Input**:
- User's project description
- Any additional context or constraints

**Output**:
- Requirements document
- Task breakdown with dependencies
- Risk assessment
- Success criteria

**Key Capabilities**:
- Parse natural language requirements
- Identify ambiguities and clarifications needed
- Break down into atomic tasks
- Detect dependencies between tasks
- Estimate complexity
- Flag risks and concerns

---

### 2. Architecture Agent
**File**: [02-architecture-agent.md](02-architecture-agent.md)

**Role**: System Architect

**Responsibility**: Design system architecture and define contracts

**Input**:
- Requirements from Planning Agent
- Task breakdown

**Output**:
- System architecture diagram
- Component specifications
- API contracts
- Database schema
- Data flow design

**Key Capabilities**:
- Design scalable architectures
- Define component boundaries
- Create API specifications
- Design database schemas
- Identify integration points
- Plan data flows

---

### 3. Frontend Development Agent
**File**: [03-frontend-agent.md](03-frontend-agent.md)

**Role**: UI/UX Developer

**Responsibility**: Generate production-ready frontend code

**Input**:
- Component specifications
- API contracts
- Styling requirements

**Output**:
- React/Vue/Angular components
- TypeScript types
- Styling (Tailwind CSS)
- API client code
- Tests

**Key Capabilities**:
- Generate component code
- Type-safe interfaces
- Responsive design
- Accessibility (WCAG)
- State management
- API integration

---

### 4. Backend Development Agent
**File**: [04-backend-agent.md](04-backend-agent.md)

**Role**: API Developer

**Responsibility**: Generate production-ready backend code

**Input**:
- API specifications
- Database schema
- Business logic requirements

**Output**:
- FastAPI/Django endpoints
- Pydantic models
- Database models
- Business logic
- Tests

**Key Capabilities**:
- Generate API endpoints
- Create database models
- Implement business logic
- Add validation
- Error handling
- Authentication/authorization

---

### 5. Backtesting & QA Agent
**File**: [05-backtesting-qa-agent.md](05-backtesting-qa-agent.md)

**Role**: Quality Assurance

**Responsibility**: Test code and validate quality

**Input**:
- Frontend code
- Backend code
- Test requirements

**Output**:
- Test suite
- Coverage report
- Bug reports
- Quality score
- Recommendations

**Key Capabilities**:
- Generate tests
- Run pytest (backend) and Vitest (frontend)
- Measure code coverage
- Identify bugs
- Validate performance
- Check security

---

### 6. Documentation Agent
**File**: [06-documentation-agent.md](06-documentation-agent.md)

**Role**: Technical Writer

**Responsibility**: Generate comprehensive documentation

**Input**:
- All project artifacts
- Code files
- Test results

**Output**:
- README
- API documentation
- Deployment guide
- User guide
- Troubleshooting guide

**Key Capabilities**:
- Generate README
- Create API docs
- Write deployment guides
- Document architecture
- Create troubleshooting guides
- Generate examples

---

## Specialist Agents (5 - Optional)

These agents provide specialized expertise in specific domains. Use when you need advanced capabilities.

### 7. Contract Validator Agent
**File**: [07-contract-validator-agent.md](07-contract-validator-agent.md)

**Role**: API Contract Validator

**Responsibility**: Validate frontend-backend API contracts match

**Input**:
- Frontend code (TypeScript types)
- Backend code (Pydantic models)
- API specifications

**Output**:
- Contract validation report
- Mismatches identified
- Recommendations
- Auto-fixes applied

**Key Capabilities**:
- Compare TypeScript interfaces with Pydantic models
- Validate request/response schemas
- Check status codes
- Verify error handling
- Auto-generate client types

---

### 8. Component Designer Agent
**File**: [08-component-designer-agent.md](08-component-designer-agent.md)

**Role**: Advanced UI Component Designer

**Responsibility**: Design advanced, accessible UI components

**Input**:
- Component requirements
- Design specifications
- Accessibility constraints

**Output**:
- Advanced components
- Storybook documentation
- Accessibility audit
- Performance optimizations

**Key Capabilities**:
- Design complex components
- Implement accessibility (WCAG AAA)
- Create component libraries
- Write Storybook stories
- Optimize rendering
- Add animations

---

### 9. Data Modeler Agent
**File**: [09-data-modeler-agent.md](09-data-modeler-agent.md)

**Role**: Database Architect

**Responsibility**: Design optimal database schemas

**Input**:
- Business requirements
- Data access patterns
- Scale requirements

**Output**:
- Optimized schema
- Indices and constraints
- Migration scripts
- Query optimization
- Backup strategy

**Key Capabilities**:
- Design relational schemas
- Create indices
- Design foreign keys
- Denormalization suggestions
- Query optimization
- Migration planning

---

### 10. Security Reviewer Agent
**File**: [10-security-reviewer-agent.md](10-security-reviewer-agent.md)

**Role**: Security Auditor

**Responsibility**: Audit code for security vulnerabilities

**Input**:
- Frontend code
- Backend code
- Configuration files
- Dependencies

**Output**:
- Security audit report
- Vulnerabilities identified
- Remediation recommendations
- Security score

**Key Capabilities**:
- Identify OWASP Top 10 issues
- Check dependencies for vulnerabilities
- Audit authentication/authorization
- Check for injection vulnerabilities
- Validate cryptography usage
- Review secrets management

---

### 11. Performance Reviewer Agent
**File**: [11-performance-reviewer-agent.md](11-performance-reviewer-agent.md)

**Role**: Performance Specialist

**Responsibility**: Analyze and optimize performance

**Input**:
- Code (frontend & backend)
- Database schema
- Configuration
- Test results

**Output**:
- Performance audit report
- Bottlenecks identified
- Optimization recommendations
- Load testing results

**Key Capabilities**:
- Identify performance bottlenecks
- Analyze database queries
- Optimize frontend bundle
- Recommend caching strategies
- Load testing
- Profiling analysis

---

## Agent Communication Protocol

See [AGENT_INTERACTION_PROTOCOL.md](AGENT_INTERACTION_PROTOCOL.md) for:
- Complete communication protocol
- State contract definitions
- Message format specifications
- Artifact schemas
- Error handling
- Handoff procedures

---

## How Agents Work

### 1. Input Validation
Each agent validates its input using `validate_input()`:
```python
def validate_input(self, state: AgentState) -> bool:
    """Check if state has all required inputs."""
    # Agent-specific validation
    return True/False
```

### 2. Processing
Agent executes main logic in `process()`:
```python
def process(self, state: AgentState) -> dict[str, Any]:
    """Execute agent logic and return state updates."""
    result = do_work()
    return {
        "artifacts": {...},
        "next_agent": "next_agent_name",
        "message": "Summary of work done"
    }
```

### 3. Execution
Orchestrator calls `execute()` which handles:
```python
def execute(self, state: AgentState) -> AgentState:
    """Full execution with validation and error handling."""
    # 1. Validate input
    if not self.validate_input(state):
        raise ValueError("Invalid input")

    # 2. Process (with retries)
    result = self.process(state)

    # 3. Apply state updates
    updated_state = state.model_copy(update=result)

    # 4. Return updated state
    return updated_state
```

---

## Agent Interaction Flow

```
Planning Agent
  ├─ Input: user_request
  ├─ Output: requirements, tasks, dependencies
  └─ Next: Architecture Agent

Architecture Agent
  ├─ Input: requirements, tasks
  ├─ Output: system design, API specs, DB schema
  └─ Next: Frontend & Backend Agents (parallel)

Frontend Agent                    Backend Agent
  ├─ Input: API specs             ├─ Input: API specs, DB schema
  ├─ Output: React components     ├─ Output: FastAPI endpoints
  └─ Next: QA Agent               └─ Next: QA Agent

QA Agent (runs once both complete)
  ├─ Input: frontend code, backend code
  ├─ Output: tests, coverage, bugs
  └─ Next: Documentation Agent

Documentation Agent
  ├─ Input: all artifacts, code, tests
  ├─ Output: README, API docs, guides
  └─ Done: Project complete!
```

---

## State Management

All agents work with a shared `AgentState` object:

```python
class AgentState(BaseModel):
    user_request: str                 # Original user request
    messages: list[AgentMessage]      # Agent communication log
    tasks: list[TaskStatus]           # Task tracking
    current_phase: str                # Current workflow phase

    # Phase outputs (populated as we proceed)
    requirements: Optional[str]       # Planning output
    architecture_doc: Optional[str]   # Architecture output
    frontend_code: dict[str, str]     # Frontend output
    backend_code: dict[str, str]      # Backend output
    test_results: Optional[dict]      # QA output
    documentation: Optional[str]      # Docs output

    # State tracking
    next_agent: Optional[str]         # Next agent to execute
    is_complete: bool                 # Workflow complete
    retry_count: int                  # Error recovery tracking
    errors: list[str]                 # Error log
```

---

## Error Handling

Each agent implements error handling:

1. **Input Validation** - Fail fast with clear error
2. **Retry Logic** - Up to 3 retries with exponential backoff
3. **Error Reporting** - Add to state.errors list
4. **Graceful Degradation** - Continue with partial results

---

## Testing Agents

Each agent should have tests:

```python
def test_agent_validates_input():
    """Agent rejects invalid input."""
    agent = MyAgent()
    state = AgentState(...)
    assert not agent.validate_input(state)

def test_agent_processes_correctly():
    """Agent produces correct output."""
    agent = MyAgent()
    state = AgentState(...)
    result = agent.process(state)
    assert "artifacts" in result
    assert result["next_agent"] is not None
```

---

## Using Specialist Agents

Specialist agents are optional. Request them by specifying needs:

**Example**: "I need advanced component library with Storybook"
→ Triggers Component Designer Agent

**Example**: "Audit for security vulnerabilities"
→ Triggers Security Reviewer Agent

**Example**: "Optimize database for scale"
→ Triggers Data Modeler Agent

---

## Extending the System

To add a custom agent:

1. **Create specification** in `agents/` directory
2. **Define input/output contracts**
3. **Implement agent class** with validation and processing
4. **Add error handling**
5. **Write tests**
6. **Register in orchestrator**
7. **Update documentation**

---

## Agent Specifications Quick Links

**Core Pipeline**:
- [Planning Agent](01-planning-agent.md)
- [Architecture Agent](02-architecture-agent.md)
- [Frontend Agent](03-frontend-agent.md)
- [Backend Agent](04-backend-agent.md)
- [QA Agent](05-backtesting-qa-agent.md)
- [Documentation Agent](06-documentation-agent.md)

**Specialist Agents**:
- [Contract Validator](07-contract-validator-agent.md)
- [Component Designer](08-component-designer-agent.md)
- [Data Modeler](09-data-modeler-agent.md)
- [Security Reviewer](10-security-reviewer-agent.md)
- [Performance Reviewer](11-performance-reviewer-agent.md)

**Protocols**:
- [Agent Interaction Protocol](AGENT_INTERACTION_PROTOCOL.md)

---

## Quick Reference

| Agent | Input | Output | Time |
|-------|-------|--------|------|
| Planning | user_request | requirements, tasks | 1-2 min |
| Architecture | requirements | design, API specs | 1-2 min |
| Frontend | API specs | React components | 2-3 min |
| Backend | API specs, DB schema | FastAPI endpoints | 2-3 min |
| QA | code files | tests, coverage | 2-3 min |
| Documentation | all artifacts | README, docs | 1 min |

---

## Support

- **Questions about agents?** Check relevant agent specification file
- **Implementation details?** See [AGENT_INTERACTION_PROTOCOL.md](AGENT_INTERACTION_PROTOCOL.md)
- **Building integrations?** Check main [README.md](../README_GITHUB.md)
- **Issues?** File a GitHub issue

---

**Last Updated**: March 2026
**Status**: Complete & Production Ready ✓

See [main documentation index](../docs/INDEX.md) for complete guides.
