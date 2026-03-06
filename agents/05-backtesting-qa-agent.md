# Backtesting & QA Agent Specification

## Overview

The Backtesting & QA Agent validates all generated code through comprehensive testing. It generates test cases, runs tests, calculates code coverage, identifies bugs, and provides detailed quality reports. This agent ensures that the implementation meets quality standards before proceeding to documentation.

## Role and Responsibilities

### Primary Responsibility
Generate and execute comprehensive tests for frontend and backend code, ensuring quality and correctness.

### Secondary Responsibilities
- Generate unit tests for all components/functions
- Generate integration tests for API endpoints
- Run test suites (pytest, Vitest)
- Calculate code coverage
- Identify bugs and issues
- Validate code against requirements
- Performance testing (if specified)
- Security scanning (basic)

### What This Agent Does NOT Do
- ❌ Fix bugs (reports them for dev agents)
- ❌ Write implementation code
- ❌ Make architecture decisions
- ❌ Deploy applications

---

## Input Requirements

### Required Inputs

From `AgentState`:

| Field | Type | Description |
|-------|------|-------------|
| `frontend_code` | `dict[str, str]` | Frontend files from Frontend Agent |
| `backend_code` | `dict[str, str]` | Backend files from Backend Agent |
| `requirements` | `str` | Original requirements |
| `architecture_doc` | `str` | Architecture specs |

### Validation Rules

```python
def validate_input(self, state: AgentState) -> bool:
    """Validate that code exists to test."""
    has_frontend = bool(state.frontend_code)
    has_backend = bool(state.backend_code)

    if not (has_frontend or has_backend):
        self.logger.error("No code to test")
        return False

    # Check requirements exist
    if not state.requirements:
        self.logger.warning("No requirements for validation")

    return True
```

---

## Output Specifications

### Primary Outputs

```python
{
    "test_results": {
        "backend": {
            "total": 45,
            "passed": 43,
            "failed": 2,
            "skipped": 0,
            "duration_seconds": 12.5,
            "coverage_percent": 87.3
        },
        "frontend": {
            "total": 28,
            "passed": 28,
            "failed": 0,
            "skipped": 0,
            "duration_seconds": 8.2,
            "coverage_percent": 82.1
        },
        "overall": {
            "total": 73,
            "passed": 71,
            "failed": 2,
            "coverage_percent": 85.2,
            "status": "failed"  # or "passed"
        }
    },

    "bug_reports": [
        {
            "severity": "high",
            "component": "backend.routers.todos.create_todo",
            "description": "Missing validation for empty todo text",
            "test_case": "test_create_todo_empty_text",
            "expected": "HTTP 400 Bad Request",
            "actual": "HTTP 201 Created with empty todo",
            "file": "backend/routers/todos.py",
            "line": 45,
            "fix_suggestion": "Add Pydantic validator: @field_validator('text') def validate_text(cls, v): ..."
        }
    ],

    "coverage_report": {
        "backend/routers/auth.py": 95.0,
        "backend/routers/todos.py": 78.5,
        "backend/services/auth_service.py": 92.0,
        "frontend/components/LoginForm.tsx": 85.0,
        "frontend/components/TodoList.tsx": 80.0
    },

    "message": "Tests: 71/73 passed (2 failures). Coverage: 85.2%",
    "current_phase": "testing",
    "next_agent": "frontend" if has_failures else "documentation",
    "requires_human_approval": True if critical_failures else False
}
```

### Error Analysis and Intelligent Restart (NEW)

When tests fail, QA Agent performs detailed error analysis and generates intelligent restart plans:

```python
{
    # ... existing test_results, bug_reports, coverage_report ...

    "error_analysis": {
        "root_cause": "api_contract_mismatch",  # or "code_bug", "spec_issue", "both"
        "affected_agents": ["frontend"],  # Which agents generated the failures
        "severity": "high",  # critical, high, medium, low
        "details": {
            "mismatch_type": "unexpected_request_field",
            "endpoint": "POST /api/todos",
            "frontend_sends": "priority: string",
            "backend_expects": "not present in schema",
            "error_message": "TypeError: unexpected keyword argument 'priority'"
        },
        "recommendation": "Frontend Agent sent 'priority' field which backend doesn't support. Either add 'priority' to backend API spec or remove from frontend code."
    },

    "restart_plan": {
        "error_analysis": { ... },  # Full error analysis above
        "agents_to_restart": ["backend"],  # Ordered list of agents to re-execute
        "execution_order": ["backend", "qa"],  # With downstream agents
        "reason": "Backend API spec must be updated to include 'priority' field",
        "expected_outcome": "Backend implements priority support, Frontend tests pass"
    }
}
```

---

### Error Analysis Root Causes

The QA Agent analyzes failures and categorizes root causes:

**1. API Contract Mismatch** (`api_contract_mismatch`)
- Frontend calls API that doesn't exist in backend
- Frontend sends fields not in backend schema
- Backend returns fields frontend doesn't expect
- **Action**: Regenerate Frontend and Backend with updated contract

**2. Code Bug in Frontend** (`frontend_code`)
- Test failure in frontend-specific logic
- Component state management issue
- Incorrect event handling
- **Action**: Regenerate Frontend Agent code

**3. Code Bug in Backend** (`backend_code`)
- Test failure in backend logic
- API endpoint bug
- Database query issue
- **Action**: Regenerate Backend Agent code

**4. Architecture Issue** (`architecture`)
- Fundamental design flaw
- Incompatible component specifications
- Database schema doesn't match API contracts
- **Action**: Regenerate Architecture + all downstream agents

**5. Specification Issue** (`spec`)
- Conflict between requirements and design
- Ambiguous API specification
- **Action**: May require human clarification

### Restart Plan Generation Logic

```python
def generate_restart_plan(failure_analysis):
    """
    Determine which agents to restart based on failure analysis.

    Dependency ordering:
    - planning → architecture → frontend/backend → qa → documentation

    Rules:
    1. If code issue: restart only affected agent (frontend or backend)
    2. If contract mismatch: restart both frontend and backend
    3. If architecture issue: restart architecture + all downstreams
    4. If spec issue: may need human approval
    """

    if failure_analysis.root_cause == "frontend_code":
        return restart_plan(agents=["frontend"], reason="Frontend code bug")

    elif failure_analysis.root_cause == "backend_code":
        return restart_plan(agents=["backend"], reason="Backend code bug")

    elif failure_analysis.root_cause == "api_contract_mismatch":
        # Both need to sync up
        return restart_plan(
            agents=["frontend", "backend"],
            reason="API specification mismatch"
        )

    elif failure_analysis.root_cause == "architecture":
        # Everything downstream needs rebuild
        return restart_plan(
            agents=["architecture", "frontend", "backend"],
            reason="Fundamental architecture issue"
        )

    else:  # "spec" or other
        return restart_plan(
            agents=[],
            reason="Requires human review and clarification"
        )
```

### Execution Status Tracking

For intelligent restart, QA tracks version information:

```python
{
    "execution_status": {
        "frontend": {
            "status": "completed",
            "version": 1,
            "depends_on": {"architecture": 1, "contract_validator": 1},
            "tests_passed": False
        },
        "backend": {
            "status": "completed",
            "version": 1,
            "depends_on": {"architecture": 1, "contract_validator": 1},
            "tests_passed": True
        }
    }
}
```

When Frontend is regenerated:
```python
{
    "execution_status": {
        "frontend": {
            "status": "completed",
            "version": 2,  # ← Incremented!
            "depends_on": {"architecture": 1, "contract_validator": 1},
            "tests_passed": True  # ← Hopefully!
        },
        "backend": {
            "status": "completed",
            "version": 1,  # ← Unchanged (reused)
            "depends_on": {"architecture": 1, "contract_validator": 1},
            "tests_passed": True
        }
    }
}
```

---

## LLM Configuration

```python
{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.1,
    "max_tokens": 8192,
    "timeout": 300
}
```

**Rationale:**
- **Very low temperature (0.1)**: Testing requires precision and consistency
- **Longer timeout**: Running tests can take time

---

## System Prompt

```
You are an expert QA engineer and test automation specialist with deep debugging skills.

Your responsibilities:
1. Generate comprehensive test suites
2. Write unit tests for all functions/components
3. Write integration tests for APIs
4. Calculate code coverage
5. Identify bugs and edge cases
6. Validate against requirements
7. Provide actionable bug reports
8. [NEW] Analyze test failures and identify root causes
9. [NEW] Generate intelligent restart plans for failures

Error Analysis (NEW):
When tests fail, analyze and categorize the root cause:
- API Contract Mismatch: Frontend/Backend API specs don't align
- Code Bug: Logic error in generated code
- Architecture Issue: Fundamental design flaw
- Specification Issue: Requirements conflict

Restart Planning (NEW):
Based on root cause analysis, generate a restart_plan that specifies:
- Which agents should be re-executed
- Correct execution order (respecting dependencies)
- Reason for restart
- Expected outcome

Example Analysis:
```
Failure: Frontend test fails with "POST /api/todos/123/assign - 404 Not Found"

Analysis:
- Frontend calls: POST /api/todos/123/assign (missing endpoint)
- Backend spec: Only has POST /api/todos and PUT /api/todos/:id
- Root cause: API CONTRACT MISMATCH
- Affected agents: [backend]
- Reason: Architecture spec changed, backend implementation didn't catch it
- Restart plan: Regenerate Backend with latest architecture

OR if spec issue:

Failure: Test expects todos to have 'priority' field, but backend returns 'urgency'

Analysis:
- Architecture spec: priority (string enum: low, medium, high)
- Backend generated: urgency field instead
- Root cause: BACKEND CODE BUG
- Affected agents: [backend]
- Restart plan: Regenerate Backend Agent with correction
```

Testing Principles:
- Test behavior, not implementation
- Arrange-Act-Assert pattern
- Descriptive test names
- One assertion per test (when possible)
- Test edge cases and error conditions
- Mock external dependencies

Python Testing (pytest):
```python
def test_feature_name_scenario():
    """Test that feature_name does X when Y."""
    # Arrange
    setup_data = ...

    # Act
    result = function_under_test(setup_data)

    # Assert
    assert result == expected_value
    assert other_condition
```

TypeScript Testing (Vitest):
```typescript
describe('ComponentName', () => {
  it('should render with props', () => {
    // Arrange
    const props = { ... };

    // Act
    render(<ComponentName {...props} />);

    // Assert
    expect(screen.getByText('...')).toBeInTheDocument();
  });
});
```

Test Coverage Goals:
- Overall: 80%+
- Critical paths: 100%
- Happy path + error cases
- Edge cases and boundary conditions

Bug Report Format:
- Severity (critical, high, medium, low)
- Component/file affected
- Description of issue
- Expected vs actual behavior
- Steps to reproduce
- Fix suggestion

Quality Criteria:
✅ All tests pass
✅ Coverage > 80%
✅ No critical bugs
✅ API tests cover all endpoints
✅ Component tests cover user interactions
✅ Error handling tested
```

---

## Tools and Capabilities

| Tool | Purpose |
|------|---------|
| `run_pytest` | Execute Python tests |
| `run_vitest` | Execute frontend tests |
| `check_coverage` | Calculate coverage |
| `validate_code` | Static analysis |

---

## Success Criteria

### Testing Success
✅ All tests generated
✅ Tests executed successfully
✅ Coverage > 80%
✅ Bugs identified and reported
✅ Critical bugs flagged for immediate fix

### [NEW] Error Analysis Success
✅ Root cause correctly identified for all failures
✅ Affected agents correctly determined
✅ Restart plan is valid (respects dependencies)
✅ Restart plan achieves expected outcome (when executed)

---

## Workflow Integration

### Next Steps After QA

**If tests pass:**
```
QA Agent ✅
   ↓
Documentation Agent (next_agent = "documentation")
```

**If tests fail (non-critical, with restart plan):**
```
QA Agent ❌ (generates restart_plan)
   ↓
Orchestrator reads restart_plan
   ↓
[Selective Restart]
├─ If code_bug in backend:
│  └─ Backend Agent (regenerate)
│
├─ If code_bug in frontend:
│  └─ Frontend Agent (regenerate)
│
├─ If api_contract_mismatch:
│  ├─ Backend Agent (regenerate)
│  └─ Frontend Agent (regenerate)
│
└─ If architecture_issue:
   ├─ Architecture Agent (regenerate)
   ├─ Backend Agent (regenerate)
   └─ Frontend Agent (regenerate)

   ↓
QA Agent (retest)
   ↓
[Repeat until pass or max retries]
```

**If tests fail and requires human approval:**
```
QA Agent ❌ (cannot auto-fix)
   ↓
requires_human_approval = True
   ↓
Human Review (clarify spec or fix architecture)
   ↓
[Restart affected agents per human guidance]
   ↓
QA Agent (retest)
```

### Intelligent Restart Flow (NEW)

The orchestrator uses QA's `restart_plan` to make intelligent decisions:

1. **Parse restart_plan** from QA Agent output
2. **Validate dependencies**: Check execution order
3. **Check version compatibility**: Ensure upstream agents match expectations
4. **Execute in order**: Frontend/Backend in parallel if independent
5. **Pass context**: Only necessary artifacts to each agent
6. **Re-execute QA**: Rerun tests with fresh code
7. **Compare results**: Track if test pass rate improved
8. **Retry logic**: Up to 3 attempts per agent, with exponential backoff

**Version Tracking Example:**
```
Initial State:
  - architecture: v1
  - frontend: v1 (depends on architecture v1) ✅
  - backend: v1 (depends on architecture v1) ✅

Test Failure: frontend tests fail due to API mismatch

QA Analysis → Restart Plan:
  agents_to_restart: ["backend"]  # Only backend

After restart:
  - architecture: v1 (unchanged)
  - frontend: v1 (unchanged, reuses)
  - backend: v2 (regenerated)

QA runs again → Tests pass!
```

---

## Examples

### Example Test Output

```python
{
    "test_results": {
        "backend": {
            "total": 12,
            "passed": 11,
            "failed": 1,
            "coverage_percent": 85.0
        }
    },

    "bug_reports": [
        {
            "severity": "medium",
            "component": "POST /api/v1/todos",
            "description": "Missing validation for text field length",
            "expected": "Reject todos with text > 500 chars",
            "actual": "Accepts unlimited length",
            "fix_suggestion": "Add Pydantic field validator: text: str = Field(max_length=500)"
        }
    ],

    "next_agent": "documentation"
}
```

---

**Document Version:** 2.0 (Enhanced with Error Analysis & Intelligent Restart)
**Agent ID:** qa_001
**Last Updated:** 2026-03-06

**Changes in v2.0:**
- ✨ Added error analysis section (root cause detection)
- ✨ Added intelligent restart planning
- ✨ Added execution status tracking with versioning
- ✨ Added restart flow to workflow integration
- 🎯 QA Agent now drives intelligent failure recovery
- 🔄 Supports selective re-execution based on failure type
