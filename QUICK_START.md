# Quick Start: Universal Agent Team Foundation

---

## 📦 What You Have Now

5 production-ready Python modules implementing:
- Hierarchical state management
- Artifact validation
- Context compaction (token efficiency)
- Dependency-aware context loading
- Execution checkpointing

---

## 🎯 Three Essential Use Cases

### 1. Create & Manage State

```python
from state_models import AgentState, create_initial_state

# Start a new project
state = create_initial_state(
    project_id="todo-app-2026",
    user_request="Build a todo application with React and FastAPI",
    tech_stack={"frontend": "react", "backend": "fastapi"}
)

# Access sections
state.planning_artifacts.requirements = "..."
state.architecture_artifacts.api_specs = {...}
state.development.frontend.code_files = {...}
state.development.backend.code_files = {...}

# Add messages
from state_models import AgentMessage
msg = AgentMessage(
    agent_id="planning_001",
    role="planning",
    content="Requirements analyzed",
    artifacts={"requirements": "..."}
)
state.add_message(msg)

# Get current status
print(f"Phase: {state.metadata.current_phase}")
print(f"Complexity: {state.planning_artifacts.complexity_score}")
```

### 2. Validate Agent Outputs

```python
from artifact_schemas import SchemaValidator, QAAgentOutput

# QA Agent produces output
qa_output = {
    "test_results": {...},
    "bug_reports": [...],
    "coverage_percent": 87.5,
    "error_analysis": {...},
    "restart_plan": {...}
}

# Validate immediately
if SchemaValidator.validate_qa_output(qa_output):
    # Apply to state
    state.testing_artifacts = QAAgentOutput(**qa_output)
else:
    print("Invalid QA output!")
```

### 3. Load Efficient Context

```python
from dependency_context import DependencyContextLoader

# Only load what Frontend needs (not backend, testing, docs)
context = DependencyContextLoader.load_context_for_agent(
    state=state,
    agent_id="frontend"
)
# Returns: {metadata, planning, architecture}
# Omits: backend code, testing results, documentation

# Estimate tokens
tokens = DependencyContextLoader.estimate_tokens_for_agent(
    state=state,
    agent_id="frontend"
)
print(f"Frontend context: {tokens} tokens")

# Compare with full state (should be 30-70% smaller)
import json
full_size = len(json.dumps(state.model_dump()))
context_size = len(json.dumps(context))
savings = (1 - context_size/full_size) * 100
print(f"Token savings: {savings:.1f}%")
```

---

## 🔧 Advanced: Error Analysis & Restart

```python
from state_models import AgentState
from dependency_context import RestartImpactAnalyzer

# QA Agent detected test failure
error_analysis = {
    "root_cause": "api_contract_mismatch",
    "affected_agents": ["backend"],
    "severity": "high",
    "details": {
        "endpoint": "POST /api/todos",
        "frontend_sends": "priority",
        "backend_expects": "not present"
    }
}

# Determine restart chain
restart_agents = RestartImpactAnalyzer.get_restart_chain(
    failed_agent="qa",
    failure_type="spec"
)
print(f"Restart: {restart_agents}")
# Output: ['backend', 'qa']

# Check if agents really need restart
necessary = RestartImpactAnalyzer.analyze_restart_necessity(
    state=state,
    agent_to_restart="backend",
    agents_to_check=["frontend", "qa", "documentation"]
)
# Output: {frontend: True, qa: True, documentation: False}

# Estimate restart cost
costs = RestartImpactAnalyzer.estimate_restart_cost(
    state=state,
    agents_to_restart=["backend"]
)
print(f"Restart costs: {costs}")
```

---

## ✅ Checkpoint & Resume

```python
from checkpoint_manager import StreamingExecutionHandler

# Start execution
handler = StreamingExecutionHandler(
    project_id="todo-app-2026",
    agent_id="backend"
)

# Check if resumable from previous run
resume_state = handler.get_resume_state()
if resume_state:
    print("Resuming from checkpoint...")
    state = resume_state
else:
    print("Starting fresh...")
    state = create_initial_state(...)

# During execution, report progress
for step in [25, 50, 75, 100]:
    # ... do work ...
    handler.mark_step(state, f"Step {step}%", progress=step)

# On completion
final_update = StateUpdate(...)
handler.mark_complete(state, final_update)
```

---

## 🎯 Common Patterns

### Pattern 1: Agent Execution Loop

```python
from state_models import AgentState, StateUpdate, apply_state_update
from artifact_schemas import SchemaValidator

def execute_agent(agent_id, state):
    # 1. Load context (only needed sections)
    context = DependencyContextLoader.load_context_for_agent(state, agent_id)

    # 2. Call agent (your LLM call here)
    agent_output = call_agent(agent_id, context)

    # 3. Validate output
    if not validate_output(agent_id, agent_output):
        raise ValueError(f"Invalid output from {agent_id}")

    # 4. Create state update
    update = StateUpdate(
        current_agent=agent_id,
        # ... populate based on agent output ...
    )

    # 5. Apply to state
    state = apply_state_update(state, update)

    return state
```

### Pattern 2: Intelligent Restart

```python
def handle_qa_failure(state, qa_output):
    # QA detected failure
    error_analysis = qa_output.get("error_analysis", {})
    restart_plan = qa_output.get("restart_plan", {})

    if not restart_plan:
        # Cannot auto-fix, needs human
        return state

    # Get agents to restart
    agents_to_restart = restart_plan["agents_to_restart"]

    # Re-execute in order
    for agent_id in agents_to_restart:
        state = execute_agent(agent_id, state)

    # Re-run QA
    state = execute_agent("qa", state)

    return state
```

### Pattern 3: Context Efficiency

```python
def smart_context_for_agent(state, agent_id):
    # Estimate tokens first
    tokens = DependencyContextLoader.estimate_tokens_for_agent(state, agent_id)

    if tokens > 100_000:  # Too large?
        # Could compress further or use summaries
        print(f"Warning: {agent_id} context is large ({tokens} tokens)")

    return DependencyContextLoader.load_context_for_agent(state, agent_id)
```

---

## 📚 Module Quick Reference

### state_models
- `create_initial_state()`: Start new project state
- `apply_state_update()`: Apply changes to state
- `AgentState`: Main hierarchical state
- Sections: planning, architecture, development, testing, documentation

### artifact_schemas
- `SchemaValidator`: Validate all agent outputs
- Output classes: `PlanningAgentOutput`, `QAAgentOutput`, etc.

### context_compaction
- `RelevanceCalculator`: Determine what's important for each agent
- `CompressionThreshold`: Dynamic size limits by complexity
- `SummaryGenerator`: Create relevance-based summaries

### dependency_context
- `DependencyGraph`: All agent dependencies
- `DependencyContextLoader`: Load minimal context per agent
- `RestartImpactAnalyzer`: Determine restart scope

### checkpoint_manager
- `CheckpointManager`: Save/load checkpoints
- `StreamingExecutionHandler`: Track progress during execution
- `ExecutionResumer`: Continue from checkpoint

---

## 🚀 Next Steps

1. **Phase 2 (Ready)**: Orchestrator implementation
   - ProjectOrchestrator class
   - Task management
   - Orchestration loop

2. **Phase 2.5**: Update CLAUDE.md
   - New architecture sections
   - Workflow examples

3. **Phase 3**: Technology specialization
   - Frontend/Backend specializations
   - Tech stack detection

---

**Questions?** See individual module docstrings for detailed API docs.
