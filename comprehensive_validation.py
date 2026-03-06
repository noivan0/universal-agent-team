"""
Comprehensive validation of Phase 1-2.5 implementation.

Tests:
1. Module import and structure
2. Cross-module dependencies
3. Basic functionality
4. Integration points
5. Potential issues
"""

import sys
import os

# Create temp home for testing
import tempfile
os.environ["HOME"] = tempfile.mkdtemp()

print("=" * 80)
print("🔍 COMPREHENSIVE VALIDATION: Phase 1-2.5")
print("=" * 80)

# Test 1: Import all modules
print("\n📦 Test 1: Module Imports")
print("-" * 80)

import_results = {}
modules_to_test = [
    ("state_models", "Core state definitions"),
    ("artifact_schemas", "Artifact validation"),
    ("context_compaction", "Token efficiency"),
    ("dependency_context", "Dependency management"),
    ("checkpoint_manager", "Checkpoint support"),
    ("orchestrator.project_registry", "Project management"),
    ("orchestrator.team_registry", "Team management"),
    ("orchestrator.task_manager", "Task management"),
    ("orchestrator.orchestrator", "Main orchestrator"),
]

for module_name, description in modules_to_test:
    try:
        __import__(module_name)
        print(f"  ✅ {module_name:<40} | {description}")
        import_results[module_name] = True
    except Exception as e:
        print(f"  ❌ {module_name:<40} | ERROR: {str(e)[:50]}")
        import_results[module_name] = False

# Test 2: Check key classes exist
print("\n🏗️  Test 2: Key Classes Existence")
print("-" * 80)

from state_models import (
    AgentState, ProjectMetadata, AgentMessage, ExecutionStatusTracker,
    create_initial_state, apply_state_update
)
from artifact_schemas import (
    PlanningAgentOutput, ArchitectureAgentOutput, QAAgentOutput,
    SchemaValidator
)
from context_compaction import RelevanceCalculator, CompressionThreshold
from dependency_context import DependencyGraph, DependencyContextLoader
from checkpoint_manager import CheckpointManager, StreamingExecutionHandler
from orchestrator.project_registry import ProjectRegistry, ProjectConfig
from orchestrator.team_registry import TeamRegistry, TeamConfig
from orchestrator.task_manager import TaskManager, TaskRecord
from orchestrator.orchestrator import ProjectOrchestrator

classes_to_check = [
    (AgentState, "AgentState"),
    (ProjectMetadata, "ProjectMetadata"),
    (ExecutionStatusTracker, "ExecutionStatusTracker"),
    (RelevanceCalculator, "RelevanceCalculator"),
    (DependencyGraph, "DependencyGraph"),
    (CheckpointManager, "CheckpointManager"),
    (ProjectRegistry, "ProjectRegistry"),
    (TeamRegistry, "TeamRegistry"),
    (TaskManager, "TaskManager"),
    (ProjectOrchestrator, "ProjectOrchestrator"),
]

for cls, name in classes_to_check:
    try:
        assert cls is not None
        print(f"  ✅ {name:<30} | Class definition found")
    except Exception as e:
        print(f"  ❌ {name:<30} | ERROR: {str(e)}")

# Test 3: Create initial state
print("\n💾 Test 3: State Creation & Operations")
print("-" * 80)

try:
    state = create_initial_state(
        project_id="validation-test",
        user_request="Test project"
    )
    print(f"  ✅ Create initial state | project_id={state.metadata.project_id}")

    # Check state structure
    assert hasattr(state, 'metadata'), "Missing metadata section"
    assert hasattr(state, 'planning_artifacts'), "Missing planning_artifacts section"
    assert hasattr(state, 'architecture_artifacts'), "Missing architecture_artifacts section"
    assert hasattr(state, 'development'), "Missing development section"
    assert hasattr(state, 'testing_artifacts'), "Missing testing_artifacts section"
    assert hasattr(state, 'documentation_artifacts'), "Missing documentation_artifacts section"
    assert hasattr(state, 'execution_status'), "Missing execution_status section"
    print(f"  ✅ State structure | All 7 sections present")

    # Test update
    from state_models import StateUpdate
    update = StateUpdate(current_phase="architecture")
    updated_state = apply_state_update(state, update)
    assert updated_state.metadata.current_phase.value == "architecture"
    print(f"  ✅ State update | Phase changed to architecture")

except Exception as e:
    print(f"  ❌ State operations | ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 4: Registry operations
print("\n📋 Test 4: Registry Operations")
print("-" * 80)

try:
    # Create project
    config = ProjectRegistry.create_project(
        project_id="test-registry-1",
        user_request="Test"
    )
    print(f"  ✅ ProjectRegistry.create_project | project_id={config.project_id}")

    # Load project
    loaded = ProjectRegistry.load_project_config("test-registry-1")
    assert loaded is not None
    print(f"  ✅ ProjectRegistry.load_project_config | Loaded successfully")

    # Create team
    team = TeamRegistry.create_universal_team()
    print(f"  ✅ TeamRegistry.create_universal_team | team_id={team.team_id}")
    print(f"     └─ {len(team.agents)} agents configured")

    # Load team
    loaded_team = TeamRegistry.load_team_config("universal-agents-v1")
    assert loaded_team is not None
    print(f"  ✅ TeamRegistry.load_team_config | Loaded successfully")

    # Check dependencies
    deps = TeamRegistry.get_team_dependencies("universal-agents-v1")
    assert "planning" in deps
    assert "architecture" in deps
    print(f"  ✅ TeamRegistry.get_team_dependencies | Dependencies intact")

except Exception as e:
    print(f"  ❌ Registry operations | ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 5: Task management
print("\n✓ Test 5: Task Management")
print("-" * 80)

try:
    # Create tasks
    ProjectRegistry.create_project("test-tasks-1", "Test")
    dependencies = {
        "planning": [],
        "architecture": ["planning"],
        "frontend": ["architecture"],
        "backend": ["architecture"],
        "qa": ["frontend", "backend"],
        "documentation": ["qa"]
    }

    tasks = TaskManager.create_tasks_for_project("test-tasks-1", dependencies)
    print(f"  ✅ TaskManager.create_tasks_for_project | {len(tasks)} tasks created")

    # Get ready tasks
    ready = TaskManager.get_ready_tasks("test-tasks-1")
    assert len(ready) == 1
    assert ready[0].agent_id == "planning"
    print(f"  ✅ TaskManager.get_ready_tasks | Planning task ready (no deps)")

    # Get next task
    next_task = TaskManager.get_next_task("test-tasks-1")
    assert next_task is not None
    print(f"  ✅ TaskManager.get_next_task | {next_task.agent_id} is next")

    # Update task status
    from orchestrator.task_manager import TaskStatus
    TaskManager.update_task_status(
        "test-tasks-1",
        next_task.task_id,
        TaskStatus.COMPLETED
    )
    print(f"  ✅ TaskManager.update_task_status | Task marked completed")

    # Check new ready tasks
    ready = TaskManager.get_ready_tasks("test-tasks-1")
    assert len(ready) == 1
    assert ready[0].agent_id == "architecture"
    print(f"  ✅ Task ordering works | Architecture now ready (planning done)")

except Exception as e:
    print(f"  ❌ Task management | ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 6: Orchestrator
print("\n🎯 Test 6: ProjectOrchestrator")
print("-" * 80)

try:
    TeamRegistry.ensure_universal_team()
    ProjectRegistry.create_project("test-orch-1", "Test orchestrator")

    orch = ProjectOrchestrator("test-orch-1")
    print(f"  ✅ ProjectOrchestrator.__init__ | Initialized successfully")

    status = orch.get_current_status()
    assert status["project_id"] == "test-orch-1"
    assert "task_summary" in status
    print(f"  ✅ ProjectOrchestrator.get_current_status | Status retrieved")

    next_task = orch.get_next_task()
    assert next_task is not None
    print(f"  ✅ ProjectOrchestrator.get_next_task | First task is {next_task.agent_id}")

    can_proceed = orch.can_proceed()
    assert can_proceed == True
    print(f"  ✅ ProjectOrchestrator.can_proceed | Can proceed (no approvals needed)")

    report = orch.get_execution_report()
    assert report["project_id"] == "test-orch-1"
    print(f"  ✅ ProjectOrchestrator.get_execution_report | Report generated")

except Exception as e:
    print(f"  ❌ ProjectOrchestrator | ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 7: Context compaction
print("\n🔧 Test 7: Context Compaction")
print("-" * 80)

try:
    from context_compaction import RelevanceCalculator, CompressionThreshold

    # Test relevance scoring
    score = RelevanceCalculator.calculate_relevance("api_specs", "frontend")
    assert score.score > 0
    print(f"  ✅ RelevanceCalculator.calculate_relevance | Score: {score.score} ({score.relevance.value})")

    # Test threshold
    threshold = CompressionThreshold.get_threshold_for_complexity(50)
    assert threshold is not None
    print(f"  ✅ CompressionThreshold.get_threshold_for_complexity | Max size: {threshold['max_artifact_size']} bytes")

except Exception as e:
    print(f"  ❌ Context compaction | ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 8: Dependency context
print("\n📊 Test 8: Dependency Context")
print("-" * 80)

try:
    from dependency_context import DependencyGraph

    # Test dependencies
    planning_deps = DependencyGraph.get_dependencies("planning")
    assert planning_deps == []
    print(f"  ✅ DependencyGraph.get_dependencies | Planning has {len(planning_deps)} dependencies")

    arch_deps = DependencyGraph.get_dependencies("architecture")
    assert "planning" in arch_deps
    print(f"  ✅ DependencyGraph.get_dependencies | Architecture depends on {len(arch_deps)} agents")

    # Test execution order
    order = DependencyGraph.get_execution_order()
    assert order[0] == "planning"
    assert order.index("architecture") < order.index("frontend")
    print(f"  ✅ DependencyGraph.get_execution_order | Order: {' → '.join(order)}")

except Exception as e:
    print(f"  ❌ Dependency context | ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("📊 VALIDATION SUMMARY")
print("=" * 80)

passed = sum(1 for v in import_results.values() if v)
total = len(import_results)

print(f"\nModule imports: {passed}/{total} passed")
if passed == total:
    print("✅ All modules import successfully")
else:
    print("❌ Some modules failed to import")
    for module, result in import_results.items():
        if not result:
            print(f"   - {module}")

print("\n✅ VALIDATION COMPLETE")
print("=" * 80)
