"""Tests for the memory layer: models, local backend, memory manager.

Covers:
- MemoryFact creation and tech_stack matching
- MemoryContext rendering
- LocalMemoryBackend CRUD + filtering
- MemoryManager.build_context()
- EvaluatorScore model and to_dev_feedback()
- AgentState memory/evaluator fields
"""

import json
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

from memory.models import MemoryFact, MemoryContext, ObserverOutput
from memory.backends.local_backend import LocalMemoryBackend
from memory.memory_manager import MemoryManager, reset_memory_manager
from state_models import (
    AgentState, ProjectMetadata, EvaluatorScore, EvaluatorCriterionScore,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_backend(tmp_path):
    """LocalMemoryBackend pointing at a temporary directory."""
    return LocalMemoryBackend(base_dir=str(tmp_path), retention_days=90)


@pytest.fixture
def sample_fact():
    return MemoryFact(
        category="bug_pattern",
        project_type="fullstack-web",
        tech_stack=["react", "fastapi"],
        phase="qa",
        content="FastAPI route ordering: specific routes must precede /{id} catch-all",
        outcome="fixed in backend_agent",
        severity="critical",
        project_id="proj_test_001",
    )


@pytest.fixture
def sample_success_fact():
    return MemoryFact(
        category="success_pattern",
        project_type="fullstack-web",
        tech_stack=["react", "fastapi"],
        phase="architecture",
        content="Using Zustand slices for large state reduces re-render count by 40%",
        outcome="applied in 3 projects",
        project_id="proj_test_002",
    )


# ---------------------------------------------------------------------------
# MemoryFact
# ---------------------------------------------------------------------------

class TestMemoryFact:
    def test_fact_id_auto_generated(self, sample_fact):
        assert sample_fact.fact_id.startswith("fact_")

    def test_matches_tech_stack_overlap(self, sample_fact):
        assert sample_fact.matches_tech_stack(["react", "postgres"])

    def test_matches_tech_stack_no_overlap(self, sample_fact):
        assert not sample_fact.matches_tech_stack(["vue", "django"])

    def test_matches_tech_stack_empty_query(self, sample_fact):
        assert sample_fact.matches_tech_stack([])

    def test_matches_tech_stack_case_insensitive(self, sample_fact):
        assert sample_fact.matches_tech_stack(["REACT"])

    def test_timestamp_is_utc(self, sample_fact):
        assert sample_fact.timestamp.tzinfo is not None

    def test_serialization_roundtrip(self, sample_fact):
        dumped = sample_fact.model_dump_json()
        restored = MemoryFact.model_validate_json(dumped)
        assert restored.fact_id == sample_fact.fact_id
        assert restored.category == sample_fact.category


# ---------------------------------------------------------------------------
# MemoryContext
# ---------------------------------------------------------------------------

class TestMemoryContext:
    def test_is_empty_default(self):
        ctx = MemoryContext()
        assert ctx.is_empty()

    def test_is_not_empty_with_patterns(self):
        ctx = MemoryContext(known_bug_patterns=["pattern A"])
        assert not ctx.is_empty()

    def test_to_prompt_section_empty(self):
        ctx = MemoryContext()
        assert ctx.to_prompt_section() == ""

    def test_to_prompt_section_contains_bugs(self):
        ctx = MemoryContext(
            known_bug_patterns=["Bug pattern A", "Bug pattern B"],
            warning_flags=["Critical warning"],
        )
        section = ctx.to_prompt_section()
        assert "Memory Context" in section
        assert "Bug pattern A" in section
        assert "Critical warning" in section

    def test_to_prompt_section_limits_items(self):
        ctx = MemoryContext(
            known_bug_patterns=[f"pattern {i}" for i in range(20)],
        )
        section = ctx.to_prompt_section()
        # Should include at most MEMORY_MAX_BUG_PATTERNS
        assert section.count("- pattern") <= 8


# ---------------------------------------------------------------------------
# LocalMemoryBackend
# ---------------------------------------------------------------------------

class TestLocalMemoryBackend:
    def test_store_and_retrieve(self, tmp_backend, sample_fact):
        tmp_backend.store(sample_fact)
        results = tmp_backend.search(category="bug_pattern")
        assert len(results) == 1
        assert results[0].fact_id == sample_fact.fact_id

    def test_store_many(self, tmp_backend, sample_fact, sample_success_fact):
        tmp_backend.store_many([sample_fact, sample_success_fact])
        bug_results = tmp_backend.search(category="bug_pattern")
        success_results = tmp_backend.search(category="success_pattern")
        assert len(bug_results) == 1
        assert len(success_results) == 1

    def test_filter_by_tech_stack(self, tmp_backend, sample_fact):
        tmp_backend.store(sample_fact)
        results = tmp_backend.search(category="bug_pattern", tech_stack=["vue"])
        assert len(results) == 0
        results = tmp_backend.search(category="bug_pattern", tech_stack=["fastapi"])
        assert len(results) == 1

    def test_filter_by_project_type(self, tmp_backend, sample_fact):
        tmp_backend.store(sample_fact)
        results = tmp_backend.search(category="bug_pattern", project_type="ecommerce")
        assert len(results) == 0
        results = tmp_backend.search(category="bug_pattern", project_type="fullstack")
        assert len(results) == 1

    def test_age_filtering(self, tmp_backend):
        old_fact = MemoryFact(
            category="bug_pattern",
            project_type="web",
            phase="qa",
            content="Old bug",
            project_id="old",
            timestamp=datetime.now(timezone.utc) - timedelta(days=200),
        )
        tmp_backend.store(old_fact)
        results = tmp_backend.search(category="bug_pattern")
        assert len(results) == 0

    def test_returns_newest_first(self, tmp_backend):
        facts = [
            MemoryFact(
                category="success_pattern",
                project_type="web",
                phase="architecture",
                content=f"fact {i}",
                project_id=f"proj_{i}",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
            )
            for i in range(3)
        ]
        tmp_backend.store_many(facts)
        results = tmp_backend.search(category="success_pattern")
        timestamps = [r.timestamp for r in results]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_count(self, tmp_backend, sample_fact, sample_success_fact):
        tmp_backend.store_many([sample_fact, sample_success_fact])
        counts = tmp_backend.count()
        assert counts.get("bug_pattern") == 1
        assert counts.get("success_pattern") == 1

    def test_limit_respected(self, tmp_backend):
        facts = [
            MemoryFact(
                category="bug_pattern",
                project_type="web",
                phase="qa",
                content=f"bug {i}",
                project_id=f"p{i}",
            )
            for i in range(10)
        ]
        tmp_backend.store_many(facts)
        results = tmp_backend.search(category="bug_pattern", limit=3)
        assert len(results) == 3

    def test_invalid_json_file_skipped(self, tmp_backend):
        bad_file = tmp_backend.base_dir / "bug_pattern" / "corrupt.json"
        bad_file.write_text("NOT JSON", encoding="utf-8")
        results = tmp_backend.search(category="bug_pattern")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------

class TestMemoryManager:
    def setup_method(self):
        reset_memory_manager()

    def test_uses_local_backend_without_api_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SUPERMEMORY_API_KEY", raising=False)
        manager = MemoryManager(base_dir=str(tmp_path))
        assert isinstance(manager._backend, LocalMemoryBackend)

    def test_store_and_build_context(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SUPERMEMORY_API_KEY", raising=False)
        manager = MemoryManager(base_dir=str(tmp_path))

        fact = MemoryFact(
            category="bug_pattern",
            project_type="fullstack-web",
            tech_stack=["react"],
            phase="qa",
            content="React useEffect missing dependency warning causes stale closure",
            outcome="fixed by adding dependency array",
            severity="high",
            project_id="proj_001",
        )
        manager.store_fact(fact)

        ctx = manager.build_context(
            project_type="fullstack-web",
            tech_stack=["react", "fastapi"],
        )
        assert not ctx.is_empty()
        assert "useEffect" in ctx.known_bug_patterns[0]

    def test_build_context_empty_when_no_facts(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SUPERMEMORY_API_KEY", raising=False)
        manager = MemoryManager(base_dir=str(tmp_path))
        ctx = manager.build_context(project_type="fullstack-web")
        assert ctx.is_empty()

    def test_store_observer_output(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SUPERMEMORY_API_KEY", raising=False)
        manager = MemoryManager(base_dir=str(tmp_path))

        fact = MemoryFact(
            category="tech_decision",
            project_type="web",
            phase="architecture",
            content="Used SQLAlchemy async session for concurrent DB access",
            project_id="proj_002",
        )
        output = ObserverOutput(
            observer_type="technical",
            phase="architecture",
            facts=[fact],
            summary="Architecture decisions recorded.",
        )
        manager.store_observer_output(output)
        results = manager._backend.search(category="tech_decision")
        assert len(results) == 1

    def test_warning_flags_from_critical_bugs(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SUPERMEMORY_API_KEY", raising=False)
        manager = MemoryManager(base_dir=str(tmp_path))

        manager.store_fact(MemoryFact(
            category="bug_pattern",
            project_type="web",
            phase="qa",
            content="CRITICAL: Always set Content-Type header in fetch calls",
            severity="critical",
            project_id="proj_003",
        ))
        ctx = manager.build_context(project_type="web")
        assert len(ctx.warning_flags) == 1
        assert "Content-Type" in ctx.warning_flags[0]


# ---------------------------------------------------------------------------
# ObserverOutput
# ---------------------------------------------------------------------------

class TestObserverOutput:
    def test_empty_facts_by_default(self):
        output = ObserverOutput(observer_type="technical", phase="qa")
        assert output.facts == []

    def test_multiple_facts(self, sample_fact):
        output = ObserverOutput(
            observer_type="quality",
            phase="qa",
            facts=[sample_fact],
            summary="One critical bug found.",
        )
        assert len(output.facts) == 1
        assert output.summary == "One critical bug found."


# ---------------------------------------------------------------------------
# EvaluatorScore
# ---------------------------------------------------------------------------

class TestEvaluatorScore:
    def _make_score(self, avg=7.0, passed=True, strategy="pass"):
        return EvaluatorScore(
            criteria=[
                EvaluatorCriterionScore(
                    criterion="architecture_coherence", score=8.0,
                    feedback="Good alignment with spec.", passed=True,
                ),
                EvaluatorCriterionScore(
                    criterion="feature_completeness", score=6.0,
                    feedback="Most features implemented.", passed=True,
                ),
                EvaluatorCriterionScore(
                    criterion="code_quality", score=7.0,
                    feedback="TypeScript types present.", passed=True,
                ),
                EvaluatorCriterionScore(
                    criterion="functionality", score=7.0,
                    feedback="API integration correct.", passed=True,
                ),
            ],
            weighted_avg=avg,
            round_number=1,
            strategy=strategy,
            overall_feedback="Overall decent implementation.",
            passed=passed,
        )

    def test_passed_true_above_threshold(self):
        score = self._make_score(avg=7.5, passed=True, strategy="pass")
        assert score.passed is True

    def test_passed_false_below_threshold(self):
        score = self._make_score(avg=5.0, passed=False, strategy="refine")
        assert score.passed is False

    def test_get_criterion_found(self):
        score = self._make_score()
        c = score.get_criterion("architecture_coherence")
        assert c is not None
        assert c.score == 8.0

    def test_get_criterion_not_found(self):
        score = self._make_score()
        assert score.get_criterion("nonexistent") is None

    def test_to_dev_feedback_contains_key_info(self):
        score = self._make_score(avg=5.0, passed=False, strategy="refine")
        feedback = score.to_dev_feedback()
        assert "Evaluator Feedback" in feedback
        assert "5.0" in feedback
        assert "REFINE" in feedback
        assert "architecture_coherence" in feedback

    def test_to_dev_feedback_pivot_strategy(self):
        score = self._make_score(avg=3.0, passed=False, strategy="pivot")
        feedback = score.to_dev_feedback()
        assert "PIVOT" in feedback


# ---------------------------------------------------------------------------
# AgentState: memory fields
# ---------------------------------------------------------------------------

class TestAgentStateMemoryFields:
    def _make_state(self):
        return AgentState(
            metadata=ProjectMetadata(project_id="p1", user_request="Build a todo app")
        )

    def test_memory_context_defaults_none(self):
        state = self._make_state()
        assert state.memory_context is None

    def test_evaluator_score_defaults_none(self):
        state = self._make_state()
        assert state.evaluator_score is None

    def test_set_memory_context(self):
        state = self._make_state()
        ctx = MemoryContext(known_bug_patterns=["bug A", "bug B"])
        state.memory_context = ctx
        assert state.memory_context.known_bug_patterns == ["bug A", "bug B"]

    def test_set_evaluator_score(self):
        state = self._make_state()
        score = EvaluatorScore(
            criteria=[],
            weighted_avg=8.0,
            passed=True,
            strategy="pass",
            overall_feedback="Excellent.",
        )
        state.evaluator_score = score
        assert state.evaluator_score.weighted_avg == 8.0

    def test_state_serialization_with_memory(self):
        state = self._make_state()
        state.memory_context = MemoryContext(warning_flags=["watch out"])
        dumped = state.model_dump(mode="json")
        assert dumped["memory_context"]["warning_flags"] == ["watch out"]
