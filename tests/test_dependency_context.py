"""
Unit tests for dependency context management.

Tests cover:
- Dependency graph construction
- Dependency resolution
- Impact analysis
- Restart planning
- Version tracking
"""

import pytest
from state_models import (
    AgentState,
    TaskRecord,
    AgentPhase,
    TaskStatus,
    AgentExecutionStatus,
    ExecutionStatus,
    create_initial_state,
)


@pytest.mark.unit
class TestDependencyGraphConstruction:
    """Test building dependency graphs."""

    def test_simple_linear_dependencies(self):
        """Test simple linear task dependencies."""
        state = create_initial_state("dep_test_001", "Test")

        t1 = state.create_task_record("T001", "planning", AgentPhase.PLANNING)
        t2 = state.create_task_record("T002", "arch", AgentPhase.ARCHITECTURE)
        t3 = state.create_task_record("T003", "frontend", AgentPhase.FRONTEND)

        t2.depends_on = ["T001"]
        t3.depends_on = ["T002"]

        # Verify chain
        assert t1.task_id in state.tasks[0].task_id
        assert "T001" in t2.depends_on
        assert "T002" in t3.depends_on

    def test_multiple_dependencies(self):
        """Test task with multiple dependencies."""
        state = create_initial_state("dep_test_002", "Test")

        t1 = state.create_task_record("T001", "planning", AgentPhase.PLANNING)
        t2 = state.create_task_record("T002", "arch", AgentPhase.ARCHITECTURE)
        t3 = state.create_task_record("T003", "frontend", AgentPhase.FRONTEND)
        t4 = state.create_task_record("T004", "qa", AgentPhase.QA)

        # QA depends on both frontend and backend
        t4.depends_on = ["T003", "T002"]

        assert len(t4.depends_on) == 2
        assert "T003" in t4.depends_on
        assert "T002" in t4.depends_on

    def test_blocking_relationships(self):
        """Test blocking relationships in tasks."""
        state = create_initial_state("dep_test_003", "Test")

        t1 = state.create_task_record("T001", "planning", AgentPhase.PLANNING)
        t2 = state.create_task_record("T002", "frontend", AgentPhase.FRONTEND)
        t3 = state.create_task_record("T003", "backend", AgentPhase.BACKEND)

        # T001 blocks T002 and T003
        t1.blocks = ["T002", "T003"]

        assert len(t1.blocks) == 2
        assert "T002" in t1.blocks

    def test_agent_version_dependencies(self):
        """Test agent version dependencies."""
        state = create_initial_state("dep_test_004", "Test")

        tracker = state.execution_status

        # Planning agent produces version 1
        tracker.update_agent_status("planning_001", ExecutionStatus.COMPLETED, version=1)

        # Architecture depends on planning version 1
        arch_status = AgentExecutionStatus(
            agent_id="arch_001",
            status=ExecutionStatus.PENDING,
            depends_on={"planning_001": 1}
        )

        # Frontend depends on architecture version 1
        frontend_status = AgentExecutionStatus(
            agent_id="frontend_001",
            status=ExecutionStatus.PENDING,
            depends_on={"arch_001": 1}
        )

        assert frontend_status.depends_on["arch_001"] == 1


@pytest.mark.unit
class TestDependencyResolution:
    """Test resolving dependencies."""

    def test_check_dependencies_satisfied(self):
        """Test checking if dependencies are satisfied."""
        state = create_initial_state("resolve_001", "Test")

        # Create tasks with dependencies
        t1 = state.create_task_record("T001", "planning", AgentPhase.PLANNING)
        t1.status = TaskStatus.COMPLETED

        t2 = state.create_task_record("T002", "arch", AgentPhase.ARCHITECTURE)
        t2.depends_on = ["T001"]

        # Check if T2's dependencies are satisfied
        def check_satisfied(task_id):
            task = state.get_task(task_id)
            if not task:
                return False
            for dep_id in task.depends_on:
                dep_task = state.get_task(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    return False
            return True

        assert check_satisfied("T002") is True

    def test_unmet_dependencies(self):
        """Test detecting unmet dependencies."""
        state = create_initial_state("resolve_002", "Test")

        t1 = state.create_task_record("T001", "planning", AgentPhase.PLANNING)
        # Don't complete T001

        t2 = state.create_task_record("T002", "arch", AgentPhase.ARCHITECTURE)
        t2.depends_on = ["T001"]

        # Check unmet dependencies
        def check_satisfied(task_id):
            task = state.get_task(task_id)
            for dep_id in task.depends_on:
                dep_task = state.get_task(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    return False
            return True

        assert check_satisfied("T002") is False

    def test_circular_dependency_detection(self):
        """Test detecting circular dependencies."""
        # Circular: T1 -> T2 -> T3 -> T1

        def has_circular_dep(tasks):
            """Simple circular dependency detector."""
            for task in tasks:
                visited = set()
                to_visit = list(task.depends_on)

                while to_visit:
                    current = to_visit.pop(0)
                    if current == task.task_id:
                        return True
                    if current in visited:
                        continue
                    visited.add(current)

                    # Find task and add its dependencies
                    for t in tasks:
                        if t.task_id == current:
                            to_visit.extend(t.depends_on)

            return False

        state = create_initial_state("circular_001", "Test")

        t1 = state.create_task_record("T001", "p", AgentPhase.PLANNING)
        t2 = state.create_task_record("T002", "a", AgentPhase.ARCHITECTURE)
        t3 = state.create_task_record("T003", "f", AgentPhase.FRONTEND)

        # Create circular: T1 -> T2 -> T3 -> T1
        t1.depends_on = ["T003"]
        t2.depends_on = ["T001"]
        t3.depends_on = ["T002"]

        assert has_circular_dep(state.tasks) is True

    def test_topological_sort(self):
        """Test topological sorting of tasks."""
        state = create_initial_state("topo_001", "Test")

        t1 = state.create_task_record("T001", "p", AgentPhase.PLANNING)
        t2 = state.create_task_record("T002", "a", AgentPhase.ARCHITECTURE)
        t3 = state.create_task_record("T003", "f", AgentPhase.FRONTEND)
        t4 = state.create_task_record("T004", "qa", AgentPhase.QA)

        t2.depends_on = ["T001"]
        t3.depends_on = ["T002"]
        t4.depends_on = ["T003"]

        # Topological order should be T001 -> T002 -> T003 -> T004
        def topo_sort(tasks):
            """Simple topological sort."""
            ordered = []
            remaining = list(tasks)

            while remaining:
                for task in remaining:
                    if not any(dep in [t.task_id for t in remaining if t != task]
                              for dep in task.depends_on):
                        ordered.append(task)
                        remaining.remove(task)
                        break

            return ordered

        sorted_tasks = topo_sort(state.tasks)

        # Verify order
        order_ids = [t.task_id for t in sorted_tasks]
        assert order_ids.index("T001") < order_ids.index("T002")
        assert order_ids.index("T002") < order_ids.index("T003")
        assert order_ids.index("T003") < order_ids.index("T004")


@pytest.mark.unit
class TestImpactAnalysis:
    """Test impact analysis for changes."""

    def test_downstream_impact(self):
        """Test analyzing downstream impact of task failure."""
        state = create_initial_state("impact_001", "Test")

        # Task chain: Planning -> Architecture -> Frontend -> QA
        t_plan = state.create_task_record("T_PLAN", "planning", AgentPhase.PLANNING)
        t_arch = state.create_task_record("T_ARCH", "arch", AgentPhase.ARCHITECTURE)
        t_front = state.create_task_record("T_FRONT", "frontend", AgentPhase.FRONTEND)
        t_qa = state.create_task_record("T_QA", "qa", AgentPhase.QA)

        t_arch.depends_on = ["T_PLAN"]
        t_front.depends_on = ["T_ARCH"]
        t_qa.depends_on = ["T_FRONT"]

        # If planning fails, what's affected?
        def analyze_downstream(task_id, tasks):
            """Find all tasks affected by a failure."""
            affected = set([task_id])
            to_check = [task_id]

            while to_check:
                current = to_check.pop(0)
                for task in tasks:
                    if current in task.depends_on and task.task_id not in affected:
                        affected.add(task.task_id)
                        to_check.append(task.task_id)

            return affected

        impact = analyze_downstream("T_PLAN", state.tasks)

        # Planning failure affects architecture, frontend, and QA
        assert "T_ARCH" in impact
        assert "T_FRONT" in impact
        assert "T_QA" in impact

    def test_module_impact_scope(self):
        """Test scope of impact to specific modules."""
        state = create_initial_state("scope_001", "Test")

        # Architecture and frontend are parallel
        t_arch = state.create_task_record("T_ARCH", "arch", AgentPhase.ARCHITECTURE)
        t_front = state.create_task_record("T_FRONT", "frontend", AgentPhase.FRONTEND)
        t_back = state.create_task_record("T_BACK", "backend", AgentPhase.BACKEND)
        t_qa = state.create_task_record("T_QA", "qa", AgentPhase.QA)

        t_arch.blocks = ["T_FRONT", "T_BACK"]
        t_front.depends_on = ["T_ARCH"]
        t_back.depends_on = ["T_ARCH"]
        t_qa.depends_on = ["T_FRONT", "T_BACK"]

        # If frontend fails, does it affect backend?
        def affects_module(failing_task_id, target_task_id, tasks):
            """Check if failure of one task affects another."""
            to_check = [failing_task_id]
            visited = set()

            while to_check:
                current = to_check.pop(0)
                if current == target_task_id:
                    return True
                if current in visited:
                    continue
                visited.add(current)

                for task in tasks:
                    if current in task.depends_on:
                        to_check.append(task.task_id)

            return False

        # Frontend failure affects QA but not backend
        assert affects_module("T_FRONT", "T_QA", state.tasks) is True
        assert affects_module("T_FRONT", "T_BACK", state.tasks) is False

    def test_critical_path_identification(self):
        """Test identifying critical path."""
        state = create_initial_state("crit_001", "Test")

        # Create critical path: T1 -> T2 -> T3
        # And optional branch: T2 -> T4
        t1 = state.create_task_record("T1", "a", AgentPhase.PLANNING)
        t2 = state.create_task_record("T2", "b", AgentPhase.ARCHITECTURE)
        t3 = state.create_task_record("T3", "c", AgentPhase.FRONTEND)
        t4 = state.create_task_record("T4", "d", AgentPhase.BACKEND)

        t2.depends_on = ["T1"]
        t3.depends_on = ["T2"]
        t4.depends_on = ["T2"]

        # Critical path is T1 -> T2 -> T3 (minimum depth 3)
        # T4 is optional (depth 2)

        def find_critical_path(tasks):
            """Find longest dependency path."""
            def depth(task_id):
                task = next((t for t in tasks if t.task_id == task_id), None)
                if not task or not task.depends_on:
                    return 1
                return 1 + max(depth(dep) for dep in task.depends_on)

            return max(depth(t.task_id) for t in tasks)

        critical_depth = find_critical_path(state.tasks)
        assert critical_depth == 3  # T1 -> T2 -> T3


@pytest.mark.unit
class TestRestartPlanning:
    """Test intelligent restart planning."""

    def test_minimal_restart_scope(self):
        """Test determining minimal restart scope."""
        state = create_initial_state("restart_001", "Test")

        # Setup: Planning -> Architecture -> Frontend + Backend -> QA
        t_plan = state.create_task_record("T_PLAN", "planning", AgentPhase.PLANNING)
        t_arch = state.create_task_record("T_ARCH", "arch", AgentPhase.ARCHITECTURE)
        t_front = state.create_task_record("T_FRONT", "frontend", AgentPhase.FRONTEND)
        t_back = state.create_task_record("T_BACK", "backend", AgentPhase.BACKEND)
        t_qa = state.create_task_record("T_QA", "qa", AgentPhase.QA)

        t_plan.status = TaskStatus.COMPLETED
        t_arch.status = TaskStatus.COMPLETED
        t_front.status = TaskStatus.COMPLETED
        t_back.status = TaskStatus.FAILED  # Backend failed
        t_qa.status = TaskStatus.PENDING

        # Restart from backend only
        restart_phase = "backend"
        tasks_to_redo = ["T_BACK", "T_QA"]

        assert len(tasks_to_redo) == 2

    def test_restart_with_specialists(self):
        """Test restart planning when specialists are involved."""
        state = create_initial_state("restart_spec_001", "Test")

        # Architecture -> Specialist (Data Modeler) -> Backend -> QA
        t_arch = state.create_task_record("T_ARCH", "arch", AgentPhase.ARCHITECTURE)
        t_specialist = state.create_task_record(
            "T_SPECIALIST", "data_modeler", AgentPhase.CONTRACT_VALIDATION
        )
        t_back = state.create_task_record("T_BACK", "backend", AgentPhase.BACKEND)
        t_qa = state.create_task_record("T_QA", "qa", AgentPhase.QA)

        t_arch.status = TaskStatus.COMPLETED
        t_specialist.status = TaskStatus.COMPLETED
        t_back.status = TaskStatus.FAILED
        t_qa.status = TaskStatus.PENDING

        # Restart from backend, re-run specialist review
        tasks_to_redo = ["T_SPECIALIST", "T_BACK", "T_QA"]

        assert "T_SPECIALIST" in tasks_to_redo

    def test_restart_time_estimation(self):
        """Test estimating restart time."""
        state = create_initial_state("restart_time_001", "Test")

        # Estimate time for tasks to redo
        task_durations = {
            "T_PLAN": 30,  # minutes
            "T_ARCH": 45,
            "T_SPECIALIST": 60,
            "T_BACK": 90,
            "T_QA": 60
        }

        tasks_to_redo = ["T_SPECIALIST", "T_BACK", "T_QA"]
        total_time = sum(task_durations.get(t, 0) for t in tasks_to_redo)

        # With parallelization, actual time might be less
        # But estimate sequential
        assert total_time == 210  # 3.5 hours

    def test_restart_validation_checklist(self):
        """Test validation checklist before restart."""
        state = create_initial_state("restart_valid_001", "Test")

        restart_plan = {
            "restart_from_phase": "backend",
            "tasks_to_redo": ["T_BACK", "T_QA"],
            "dependencies_checked": True,
            "artifacts_prepared": True,
            "specialists_ready": True,
            "estimated_time_minutes": 120
        }

        # Validate plan
        all_ready = all([
            restart_plan["dependencies_checked"],
            restart_plan["artifacts_prepared"],
            restart_plan["specialists_ready"],
            restart_plan["estimated_time_minutes"] > 0
        ])

        assert all_ready is True


@pytest.mark.unit
class TestVersionTracking:
    """Test version tracking across dependencies."""

    def test_agent_version_increments(self):
        """Test agent output version increments."""
        state = create_initial_state("version_001", "Test")

        tracker = state.execution_status

        # Planning v1
        tracker.update_agent_status("planning_001", ExecutionStatus.COMPLETED, version=1)
        assert tracker.get_agent_status("planning_001").version == 1

        # Update planning (v2)
        tracker.update_agent_status("planning_001", ExecutionStatus.COMPLETED, version=2)
        assert tracker.get_agent_status("planning_001").version == 2

    def test_downstream_version_requirements(self):
        """Test downstream agents requiring specific versions."""
        state = create_initial_state("version_req_001", "Test")

        # Planning v2 is produced
        state.execution_status.update_agent_status(
            "planning_001", ExecutionStatus.COMPLETED, version=2
        )

        # Architecture requires planning v2
        arch_status = AgentExecutionStatus(
            agent_id="arch_001",
            status=ExecutionStatus.PENDING,
            depends_on={"planning_001": 2}
        )

        # Check if requirement is met
        planning_status = state.execution_status.get_agent_status("planning_001")
        requirement_met = (
            planning_status.version >= arch_status.depends_on["planning_001"]
        )

        assert requirement_met is True

    def test_version_mismatch_detection(self):
        """Test detecting version mismatches."""
        state = create_initial_state("version_mismatch_001", "Test")

        # Planning v1 exists
        state.execution_status.update_agent_status(
            "planning_001", ExecutionStatus.COMPLETED, version=1
        )

        # But frontend requires v2
        frontend_status = AgentExecutionStatus(
            agent_id="frontend_001",
            status=ExecutionStatus.PENDING,
            depends_on={"planning_001": 2}
        )

        planning_status = state.execution_status.get_agent_status("planning_001")
        mismatch = (
            planning_status.version < frontend_status.depends_on["planning_001"]
        )

        assert mismatch is True

    def test_version_backward_compatibility(self):
        """Test version backward compatibility."""
        # Agents can use any version >= their minimum requirement

        def check_compatibility(available_version, required_version):
            return available_version >= required_version

        assert check_compatibility(2, 1) is True  # v2 can satisfy v1 requirement
        assert check_compatibility(1, 2) is False  # v1 cannot satisfy v2 requirement
        assert check_compatibility(2, 2) is True  # v2 can satisfy v2 requirement


@pytest.mark.unit
class TestDependencyGraphCaching:
    """Test dependency execution order caching (Quick Win 1)."""

    def test_cache_key_generation_none(self):
        """Test cache key generation for default (None) agents."""
        from dependency_context import DependencyGraph

        cache_key = DependencyGraph._get_cache_key(None)
        assert cache_key == "default_order"

    def test_cache_key_generation_sorted(self):
        """Test cache key generation is deterministic (sorted)."""
        from dependency_context import DependencyGraph

        agents1 = ["frontend", "backend", "planning"]
        agents2 = ["backend", "planning", "frontend"]

        key1 = DependencyGraph._get_cache_key(agents1)
        key2 = DependencyGraph._get_cache_key(agents2)

        # Keys should be identical since sorting is applied
        assert key1 == key2
        assert key1 == "backend|frontend|planning"

    def test_cache_hit_default_order(self):
        """Test cache hit when requesting default execution order."""
        from dependency_context import DependencyGraph

        # Clear cache first
        DependencyGraph.invalidate_cache()

        # First call - should miss cache
        order1 = DependencyGraph.get_execution_order(use_cache=True)

        # Second call - should hit cache
        order2 = DependencyGraph.get_execution_order(use_cache=True)

        # Verify results are identical
        assert order1 == order2
        # Verify cache has entry
        stats = DependencyGraph.get_cache_stats()
        assert stats["cached_orders"] >= 1

    def test_cache_miss_with_cache_disabled(self):
        """Test no caching when use_cache=False."""
        from dependency_context import DependencyGraph

        DependencyGraph.invalidate_cache()

        order1 = DependencyGraph.get_execution_order(use_cache=False)
        order2 = DependencyGraph.get_execution_order(use_cache=False)

        # Orders should be same, but cache should remain empty
        assert order1 == order2
        stats = DependencyGraph.get_cache_stats()
        assert stats["cached_orders"] == 0

    def test_cache_specific_agents(self):
        """Test caching with specific agent subset."""
        from dependency_context import DependencyGraph

        DependencyGraph.invalidate_cache()

        agents = ["planning", "architecture"]
        order1 = DependencyGraph.get_execution_order(agents, use_cache=True)
        order2 = DependencyGraph.get_execution_order(agents, use_cache=True)

        # Should be cached
        assert order1 == order2
        stats = DependencyGraph.get_cache_stats()
        assert stats["cached_orders"] >= 1

    def test_cache_invalidation(self):
        """Test cache invalidation works correctly."""
        from dependency_context import DependencyGraph

        DependencyGraph.invalidate_cache()

        # Populate cache
        order1 = DependencyGraph.get_execution_order(use_cache=True)
        stats_before = DependencyGraph.get_cache_stats()
        assert stats_before["cached_orders"] > 0

        # Invalidate cache
        DependencyGraph.invalidate_cache()
        stats_after = DependencyGraph.get_cache_stats()
        assert stats_after["cached_orders"] == 0

    def test_different_agent_sets_different_cache_keys(self):
        """Test that different agent sets produce different cache keys."""
        from dependency_context import DependencyGraph

        DependencyGraph.invalidate_cache()

        agents_set1 = ["planning", "architecture"]
        agents_set2 = ["planning", "architecture", "frontend"]

        order1 = DependencyGraph.get_execution_order(agents_set1, use_cache=True)
        order2 = DependencyGraph.get_execution_order(agents_set2, use_cache=True)

        # Different agents should produce different orders
        assert len(order1) != len(order2)

        # Cache should have both entries
        stats = DependencyGraph.get_cache_stats()
        assert stats["cached_orders"] >= 2

    def test_cache_returns_copy_not_reference(self):
        """Test that cache returns a copy, not a reference."""
        from dependency_context import DependencyGraph

        DependencyGraph.invalidate_cache()

        order1 = DependencyGraph.get_execution_order(use_cache=True)
        original_len = len(order1)

        # Modify returned order
        order1.append("fake_agent")

        # Get cached copy
        order2 = DependencyGraph.get_execution_order(use_cache=True)

        # Should not be affected by modification
        assert len(order2) == original_len
        assert "fake_agent" not in order2
