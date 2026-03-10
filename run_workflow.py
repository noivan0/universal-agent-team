"""
End-to-End Workflow Runner

Runs a full multi-agent workflow from a natural-language request.
Agents execute in dependency order; Frontend + Backend run in parallel.

Self-Healing Loop
-----------------
After QA runs, if critical bugs are found and `restart_needed=True`, the
runner automatically re-invokes the affected dev agents (Frontend / Backend)
with the bug reports injected as fix instructions, then re-runs QA.
This loop repeats up to MAX_HEALING_ITERATIONS times before giving up.

Usage:
    python run_workflow.py "Build a todo list app with React and FastAPI"
    python run_workflow.py  # uses default request
"""

import concurrent.futures
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("workflow_runner")

# ── Imports ───────────────────────────────────────────────────────────────────
from state_models import create_initial_state, AgentState, AgentPhase, apply_state_update
from agent_executor import execute_agent, AGENT_RUNNERS
from agent_bus import reset_bus, get_bus, ContractValidator
from agent_validators import AgentOutputValidator
from checkpoint_manager import CheckpointManager, ExecutionCheckpoint, migrate_state

# ── Constants ─────────────────────────────────────────────────────────────────
WORKFLOW_ORDER = [
    "planning",
    "architecture",
    ["frontend", "backend"],   # parallel pair
    "qa",
    "documentation",
]

# Self-healing: max times to retry dev agents after QA finds critical bugs
MAX_HEALING_ITERATIONS = 2

# Quality threshold: below this pass-rate we attempt self-healing
HEALING_PASS_RATE_THRESHOLD = 0.70  # 70 %

# Cooldown between sequential agents (reduces rate-limit pressure)
AGENT_COOLDOWN_SECONDS = 2

OUTPUT_DIR = Path("/workspace/generated")
CHECKPOINT_DIR = Path("/workspace/checkpoints")


# ============================================================================
# Validation helper
# ============================================================================

def _validate_agent_output(agent_id: str, update: object, state: AgentState) -> None:
    """
    Run AgentOutputValidator on a StateUpdate before it is applied.

    Extracts the relevant output dict from the typed StateUpdate, validates
    it, and logs issues.  Non-blocking issues are warnings; blocking issues
    are logged as errors.  The pipeline always continues (observability
    without changing apply behaviour).
    """
    # Build a representative output dict from whichever artifact was set
    output_dict: dict = {}
    if update.planning_artifacts:
        output_dict = update.planning_artifacts.model_dump()
    elif update.architecture_artifacts:
        output_dict = update.architecture_artifacts.model_dump()
    elif update.development:
        fe = update.development.frontend
        be = update.development.backend
        if agent_id == "frontend" and fe.code_files:
            output_dict = {"code_files": fe.code_files}
        elif agent_id == "backend" and be.code_files:
            output_dict = {"code_files": be.code_files}
        elif fe.code_files:
            output_dict = {"code_files": fe.code_files}
        elif be.code_files:
            output_dict = {"code_files": be.code_files}
    elif update.testing_artifacts:
        output_dict = update.testing_artifacts.model_dump()
    elif update.documentation_artifacts:
        output_dict = {"readme": update.documentation_artifacts.readme}

    if not output_dict:
        return  # Nothing to validate

    result = AgentOutputValidator.validate(agent_id, output_dict, state)
    for issue in result.issues:
        if issue.blocking:
            logger.error(
                f"[Validator] {agent_id}.{issue.field}: {issue.message} (BLOCKING)"
            )
        else:
            logger.warning(
                f"[Validator] {agent_id}.{issue.field}: {issue.message}"
            )


# ============================================================================
# Checkpoint helpers
# ============================================================================

def _save_checkpoint(state: AgentState, project_id: str, agent_id: str) -> None:
    """Save a state snapshot checkpoint after an agent completes."""
    try:
        checkpoint = ExecutionCheckpoint(
            project_id=project_id,
            agent_id=agent_id,
            checkpoint_id=f"post_{agent_id}",
            state_snapshot=state.model_dump(),
            progress=100,
            is_complete=True,
        )
        CheckpointManager.save_checkpoint(checkpoint, project_id)
        logger.debug(f"[Checkpoint] Saved post-{agent_id} checkpoint for {project_id}")
    except Exception as exc:
        logger.warning(f"[Checkpoint] Failed to save checkpoint after {agent_id}: {exc}")


def _load_checkpoint(project_id: str) -> Optional[AgentState]:
    """
    Try to resume from the last completed single-agent checkpoint.

    Scans all agent directories under the project checkpoint folder and
    returns the most recently written completed checkpoint's state.
    Returns None if no valid checkpoint exists.
    """
    project_dir = CheckpointManager.get_checkpoint_dir(project_id)
    if not project_dir.exists():
        return None

    # Collect all completed checkpoints across all agent subdirs
    import json as _json
    latest_mtime = 0.0
    latest_state: Optional[AgentState] = None

    for agent_dir in project_dir.iterdir():
        if not agent_dir.is_dir():
            continue
        for cp_file in sorted(agent_dir.glob("checkpoint-post_*.json")):
            try:
                mtime = cp_file.stat().st_mtime
                if mtime <= latest_mtime:
                    continue
                with open(cp_file) as f:
                    data = _json.load(f)
                if not data.get("is_complete"):
                    continue
                state_dict = migrate_state(data["state_snapshot"])
                candidate = AgentState(**state_dict)
                if candidate.is_complete:
                    continue  # Workflow already finished — start fresh
                latest_mtime = mtime
                latest_state = candidate
            except Exception as exc:
                logger.debug(f"[Checkpoint] Skipping {cp_file}: {exc}")

    if latest_state:
        logger.info(
            f"[Checkpoint] Resuming from checkpoint: "
            f"phase={latest_state.metadata.current_phase.value}"
        )
    return latest_state


# ============================================================================
# Parallel execution helper
# ============================================================================

def run_parallel(
    agents: List[str],
    state: AgentState,
    bug_reports: Optional[List] = None,
) -> List[Tuple[str, object, Optional[Exception]]]:
    """Run multiple agents concurrently and return (agent_id, update, error)."""

    results = []

    def _run(agent_id: str):
        try:
            return agent_id, execute_agent(agent_id, state, bug_reports=bug_reports), None
        except Exception as exc:
            return agent_id, None, exc

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as ex:
        futures = {ex.submit(_run, aid): aid for aid in agents}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    return results


# ============================================================================
# QA quality assessment helper
# ============================================================================

def _qa_needs_healing(state: AgentState) -> Tuple[bool, List, List[str]]:
    """
    Inspect QA results and decide whether self-healing should be triggered.

    Returns:
        (should_heal, bug_reports, affected_agents)
    """
    ta = state.testing_artifacts
    bug_reports = ta.bug_reports or []
    error_analysis = ta.error_analysis or {}

    critical_bugs = [
        b for b in bug_reports
        if isinstance(b, dict) and b.get("severity") == "critical"
    ]

    restart_needed = error_analysis.get("restart_needed", False)

    tr = ta.test_results or {}
    total = tr.get("total", 0)
    passed = tr.get("passed", 0)
    pass_rate = (passed / total) if total > 0 else 0.0

    low_quality = pass_rate < HEALING_PASS_RATE_THRESHOLD

    if (critical_bugs or low_quality) and restart_needed:
        affected = error_analysis.get("affected_agents", [])
        # Default: heal both if not specified
        if not affected:
            affected = ["frontend", "backend"]
        # Only heal dev agents (not planning/architecture/qa/documentation)
        affected = [a for a in affected if a in ("frontend", "backend")]
        return True, bug_reports, affected

    return False, [], []


# ============================================================================
# Self-healing loop
# ============================================================================

def run_healing_loop(state: AgentState, errors_encountered: List) -> AgentState:
    """
    Re-run affected dev agents with bug context, then re-run QA.
    Repeats up to MAX_HEALING_ITERATIONS times.

    Returns:
        Updated state after healing attempts.
    """
    for iteration in range(1, MAX_HEALING_ITERATIONS + 1):
        should_heal, bug_reports, affected = _qa_needs_healing(state)

        if not should_heal:
            logger.info(f"[Healing] No further healing needed after iteration {iteration - 1}.")
            break

        critical_count = sum(
            1 for b in bug_reports
            if isinstance(b, dict) and b.get("severity") == "critical"
        )
        logger.info(
            f"\n{'═'*50}\n"
            f"🔧 SELF-HEALING ITERATION {iteration}/{MAX_HEALING_ITERATIONS}\n"
            f"   Critical bugs: {critical_count}  |  Affected agents: {affected}\n"
            f"{'═'*50}"
        )

        # ── Re-run affected dev agents (in parallel if more than one) ──
        t0 = time.time()
        if len(affected) == 1:
            agent_id = affected[0]
            logger.info(f"  ▶ Healing agent: {agent_id.upper()}")
            try:
                update = execute_agent(agent_id, state, bug_reports=bug_reports)
                state = apply_state_update(state, update)
                if state.messages:
                    logger.info(f"  ✓ {agent_id}: {state.messages[-1].content}")
            except Exception as exc:
                logger.error(f"  ✗ {agent_id} healing FAILED: {exc}")
                errors_encountered.append((f"{agent_id}_heal_{iteration}", str(exc)))
        else:
            logger.info(f"  ▶ Healing PARALLEL: {' + '.join(a.upper() for a in affected)}")
            results = run_parallel(affected, state, bug_reports=bug_reports)
            for agent_id, update, error in results:
                if error:
                    logger.error(f"  ✗ {agent_id} healing FAILED: {error}")
                    errors_encountered.append((f"{agent_id}_heal_{iteration}", str(error)))
                else:
                    state = apply_state_update(state, update)
                    if state.messages:
                        logger.info(f"  ✓ {agent_id}: {state.messages[-1].content}")

        elapsed_dev = time.time() - t0
        logger.info(f"  Dev healing completed in {elapsed_dev:.1f}s")

        # ── Re-run QA ────────────────────────────────────────────────────
        logger.info(f"  ▶ Re-running QA (iteration {iteration})")
        t1 = time.time()
        try:
            qa_update = execute_agent("qa", state)
            state = apply_state_update(state, qa_update)
            elapsed_qa = time.time() - t1

            tr = state.testing_artifacts.test_results or {}
            bugs = state.testing_artifacts.bug_reports or []
            critical_after = sum(
                1 for b in bugs if isinstance(b, dict) and b.get("severity") == "critical"
            )
            pass_rate_after = (
                tr.get("passed", 0) / tr.get("total", 1)
                if tr.get("total", 0) > 0 else 0.0
            )
            logger.info(
                f"  ✓ QA re-run complete in {elapsed_qa:.1f}s: "
                f"{tr.get('passed', 0)}/{tr.get('total', 0)} passed "
                f"({pass_rate_after*100:.0f}%), {critical_after} critical bugs"
            )
        except Exception as exc:
            elapsed_qa = time.time() - t1
            logger.error(f"  ✗ QA re-run FAILED after {elapsed_qa:.1f}s: {exc}")
            errors_encountered.append((f"qa_heal_{iteration}", str(exc)))
            break  # Can't judge quality → stop healing

    return state


# ============================================================================
# Fallback documentation (no LLM required)
# ============================================================================

def _generate_fallback_docs(state: AgentState) -> AgentState:
    """
    Generate minimal documentation from state without calling the LLM.

    Used when the Documentation Agent fails (e.g. API quota exhausted).
    Produces a usable README and API reference from already-available state.
    """
    from state_models import DocumentationArtifacts, AgentMessage, apply_state_update, StateUpdate, AgentPhase

    logger.info("[Fallback Docs] Generating minimal docs from state (no LLM)")

    req = state.metadata.user_request
    fe_files = list(state.development.frontend.code_files.keys())
    be_files = list(state.development.backend.code_files.keys())
    tr = state.testing_artifacts.test_results or {}
    arch = state.architecture_artifacts

    # README
    readme_lines = [
        f"# {state.metadata.project_id}",
        "",
        f"> Auto-generated from: {req[:200]}",
        "",
        "## Tech Stack",
    ]
    if arch.technology_decisions:
        for k, v in arch.technology_decisions.items():
            readme_lines.append(f"- **{k}**: {v}")
    readme_lines += [
        "",
        "## Files Generated",
        f"- Frontend: {len(fe_files)} files",
        f"- Backend:  {len(be_files)} files",
        "",
        "## Test Results",
        f"- Total: {tr.get('total', 'N/A')}",
        f"- Passed: {tr.get('passed', 'N/A')}",
        f"- Coverage: {tr.get('coverage', 'N/A')}%",
        "",
        "## Quick Start",
        "```bash",
        "# Backend",
        "pip install -r requirements.txt",
        "uvicorn main:app --reload",
        "",
        "# Frontend",
        "npm install && npm run dev",
        "```",
    ]
    readme = "\n".join(readme_lines)

    # API docs
    api_lines = ["# API Documentation", ""]
    for key, ep in arch.api_specs.items():
        api_lines.append(f"## `{ep.method} {ep.path}`")
        api_lines.append(f"{ep.description}")
        if ep.authentication_required:
            api_lines.append("- **Auth required**: yes")
        api_lines.append("")
    api_docs = "\n".join(api_lines) if api_lines else "No API specs available."

    # Architecture docs
    arch_docs = arch.system_design[:1000] if arch.system_design else "No architecture doc available."

    # Deployment guide
    deploy_lines = [
        "# Deployment Guide",
        "",
        "## Requirements",
        "- Python 3.12+",
        "- Node.js 18+",
        "",
        "## Environment Variables",
        "```",
        "DATABASE_URL=sqlite:///./app.db",
        "SECRET_KEY=<your-secret-key>",
        "```",
        "",
        "## Docker",
        "```bash",
        "docker-compose up -d",
        "```",
    ]
    deploy_guide = "\n".join(deploy_lines)

    from state_models import StateUpdate
    update = StateUpdate(
        documentation_artifacts=DocumentationArtifacts(
            readme=readme,
            api_docs=api_docs,
            architecture_docs=arch_docs,
            deployment_guide=deploy_guide,
            summary="Fallback documentation generated from state (LLM unavailable).",
        ),
        current_phase=AgentPhase.COMPLETE,
        is_complete=True,
        message=AgentMessage(
            agent_id="documentation_fallback",
            role="Documentation Agent (fallback)",
            content="Minimal documentation generated from state (LLM call failed).",
        ),
    )
    return apply_state_update(state, update)


# ============================================================================
# Output writer
# ============================================================================

def save_outputs(state: AgentState, project_id: str):
    """Save generated code and documentation to /workspace/generated/."""
    base = OUTPUT_DIR / project_id
    base.mkdir(parents=True, exist_ok=True)

    # Frontend code
    if state.development.frontend.code_files:
        fe_dir = base / "frontend"
        fe_dir.mkdir(exist_ok=True)
        for path, content in state.development.frontend.code_files.items():
            dest = fe_dir / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        logger.info(f"Frontend: {len(state.development.frontend.code_files)} files → {fe_dir}")

    # Backend code
    if state.development.backend.code_files:
        be_dir = base / "backend"
        be_dir.mkdir(exist_ok=True)
        for path, content in state.development.backend.code_files.items():
            dest = be_dir / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        logger.info(f"Backend:  {len(state.development.backend.code_files)} files → {be_dir}")

    # Documentation
    docs_dir = base / "docs"
    docs_dir.mkdir(exist_ok=True)
    doc_arts = state.documentation_artifacts
    doc_map = {
        "README.md":             doc_arts.readme,
        "API_DOCS.md":           doc_arts.api_docs,
        "ARCHITECTURE.md":       doc_arts.architecture_docs,
        "DEPLOYMENT_GUIDE.md":   doc_arts.deployment_guide,
    }
    for fname, content in doc_map.items():
        if content:
            (docs_dir / fname).write_text(content, encoding="utf-8")
    logger.info(f"Docs: {len([v for v in doc_map.values() if v])} files → {docs_dir}")

    # State snapshot
    state_file = base / "state_snapshot.json"
    state_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"State snapshot → {state_file}")


# ============================================================================
# Main runner
# ============================================================================

def run_workflow(user_request: str) -> AgentState:
    """
    Execute a full multi-agent workflow for the given user request.

    Flow:
        Planning → Architecture → Frontend+Backend (parallel)
        → QA → [self-healing loop if needed] → Documentation

    Returns:
        Final AgentState after all agents have executed.
    """
    project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.info("=" * 60)
    logger.info(f"PROJECT: {project_id}")
    logger.info(f"REQUEST: {user_request}")
    logger.info("=" * 60)

    # Reset the agent message bus for this workflow run
    reset_bus()

    # Try to resume from a previous checkpoint; create fresh state if none found
    state = _load_checkpoint(project_id) or create_initial_state(
        project_id=project_id, user_request=user_request
    )
    total_start = time.time()
    errors_encountered = []

    for step in WORKFLOW_ORDER:
        agents = [step] if isinstance(step, str) else step

        # ── Single agent ────────────────────────────────────────────────
        if len(agents) == 1:
            agent_id = agents[0]
            logger.info(f"\n{'─'*50}")
            logger.info(f"▶ Running agent: {agent_id.upper()}")
            t0 = time.time()
            try:
                update = execute_agent(agent_id, state)
                _validate_agent_output(agent_id, update, state)
                state = apply_state_update(state, update)
                elapsed = time.time() - t0
                logger.info(f"✓ {agent_id} completed in {elapsed:.1f}s")

                if state.messages:
                    logger.info(f"  → {state.messages[-1].content}")

                # Save checkpoint so we can resume if interrupted later
                _save_checkpoint(state, project_id, agent_id)

                # ── Self-healing after QA ─────────────────────────────
                if agent_id == "qa":
                    state = run_healing_loop(state, errors_encountered)

            except Exception as exc:
                elapsed = time.time() - t0
                logger.error(f"✗ {agent_id} FAILED after {elapsed:.1f}s: {exc}")
                errors_encountered.append((agent_id, str(exc)))

                # ── Documentation fallback ────────────────────────────
                if agent_id == "documentation":
                    logger.warning("  ↩ Documentation failed — generating fallback docs from state")
                    try:
                        state = _generate_fallback_docs(state)
                        logger.info("  ✓ Fallback documentation generated")
                    except Exception as fallback_exc:
                        logger.error(f"  ✗ Fallback documentation also failed: {fallback_exc}")

            # Cooldown between sequential agents (reduces rate-limit pressure)
            if agent_id not in ("qa", "documentation"):
                time.sleep(AGENT_COOLDOWN_SECONDS)

        # ── Parallel agents ─────────────────────────────────────────────
        else:
            logger.info(f"\n{'─'*50}")
            logger.info(f"▶ Running PARALLEL: {' + '.join(a.upper() for a in agents)}")
            t0 = time.time()
            results = run_parallel(agents, state)
            elapsed = time.time() - t0
            logger.info(f"  Parallel batch completed in {elapsed:.1f}s")

            successful = [(aid, upd) for aid, upd, err in results if err is None]
            if not successful:
                logger.error("  ✗ All parallel agents failed — aborting workflow")
                for agent_id, _, error in results:
                    logger.error(f"    {agent_id}: {error}")
                    errors_encountered.append((agent_id, str(error)))
                break

            for agent_id, update, error in results:
                if error:
                    logger.error(f"  ✗ {agent_id} FAILED: {error}")
                    errors_encountered.append((agent_id, str(error)))
                else:
                    _validate_agent_output(agent_id, update, state)
                    state = apply_state_update(state, update)
                    _save_checkpoint(state, project_id, agent_id)
                    if state.messages:
                        logger.info(f"  ✓ {agent_id}: {state.messages[-1].content}")

            # ── Contract validation after parallel dev agents ─────────
            if set(agents) == {"frontend", "backend"}:
                logger.info("  ▶ Running API contract validation")
                contract_bugs = ContractValidator().validate(get_bus())
                if contract_bugs:
                    existing_bugs = state.testing_artifacts.bug_reports or []
                    state.testing_artifacts.bug_reports = contract_bugs + existing_bugs
                    logger.warning(
                        f"  ⚠ Contract validator found {len(contract_bugs)} violation(s) — "
                        f"added to QA bug reports"
                    )
                else:
                    logger.info("  ✓ API contracts validated — no mismatches")

    # ── Final summary ────────────────────────────────────────────────────
    total_elapsed = time.time() - total_start
    logger.info("\n" + "=" * 60)
    logger.info("WORKFLOW COMPLETE")
    logger.info(f"Total time:   {total_elapsed:.1f}s")
    logger.info(f"Final phase:  {state.metadata.current_phase.value}")
    logger.info(f"Is complete:  {state.is_complete}")
    logger.info(f"Errors:       {len(errors_encountered)}")

    if errors_encountered:
        for agent_id, err in errors_encountered:
            logger.warning(f"  ✗ {agent_id}: {err[:120]}")

    tr = state.testing_artifacts.test_results or {}
    if tr:
        total_t = tr.get("total", 0)
        passed_t = tr.get("passed", 0)
        rate = (passed_t / total_t * 100) if total_t else 0
        logger.info(
            f"Tests:  {passed_t}/{total_t} passed ({rate:.0f}%), "
            f"coverage={tr.get('coverage', 0):.1f}%"
        )

    bugs = state.testing_artifacts.bug_reports or []
    if bugs:
        critical = [b for b in bugs if isinstance(b, dict) and b.get("severity") == "critical"]
        logger.info(f"Bugs:   {len(bugs)} total, {len(critical)} critical")

    save_outputs(state, project_id)
    logger.info("=" * 60)
    return state


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    import json as _json

    api_key = (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    )
    if not api_key:
        try:
            with open(os.path.expanduser("~/.claude/settings.json")) as _f:
                _settings = _json.load(_f)
            api_key = _settings.get("env", {}).get("ANTHROPIC_AUTH_TOKEN")
        except Exception:
            pass

    if not api_key:
        print("ERROR: No API key found.")
        print("Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN environment variable.")
        sys.exit(1)

    logger.info(f"Using API key: {api_key[:12]}...")

    request = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Build a Todo List application with user authentication. "
        "Frontend: React + TypeScript + Tailwind CSS. "
        "Backend: FastAPI + SQLite. "
        "Features: Create, read, update, delete todos. Mark as complete. Filter by status."
    )

    final_state = run_workflow(request)
    sys.exit(0 if final_state.is_complete else 1)
