"""
Agent Executor — real LLM-powered execution for each specialist agent.

Each public function takes the current AgentState, calls Claude, parses the
JSON response, and returns a StateUpdate that the orchestrator applies.

Design principles
-----------------
* System prompts are concise but precise — they define the agent's role,
  exact JSON output schema, and what the agent must NOT do.
* Every agent returns well-typed output that is validated by agent_validators.
* If the LLM cannot produce valid JSON the caller catches the exception and
  records it as a PARSE_ERROR for intelligent retry.
* Agents share context only through the typed AgentState fields — no free-text
  chatter between agents (the state IS the shared memory).
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from state_models import (
    AgentState, AgentError, AgentMessage, AgentPhase, ErrorType, StateUpdate,
    PlanningArtifacts, ArchitectureArtifacts, DevelopmentArtifacts,
    DevelopmentSection, TestingArtifacts, DocumentationArtifacts,
    BrainstormingPerspective, BrainstormingArtifacts,
    EvaluatorScore, EvaluatorCriterionScore,
)
from artifact_schemas import ComponentSpec, APIEndpoint
from llm_client import LLMClient, LLMResponse, get_client
from agent_bus import get_bus
from code_runner import BackendCodeRunner, FrontendCodeRunner

logger = logging.getLogger("agent_executor")


# ============================================================================
# Shared helpers
# ============================================================================

def _filter_bugs(
    bug_reports: List[Dict[str, Any]],
    severities: Optional[List[str]] = None,
    components: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Filter bug reports by severity and/or component substring."""
    result = []
    for b in bug_reports:
        if not isinstance(b, dict):
            continue
        if severities and b.get("severity") not in severities:
            continue
        if components:
            comp = b.get("component", "").lower()
            if not any(c in comp for c in components):
                continue
        result.append(b)
    return result


def _build_project_context(state: AgentState) -> str:
    """Compact project context string injected into every agent prompt."""
    lines = [
        f"Project ID: {state.metadata.project_id}",
        f"User Request: {state.metadata.user_request}",
        f"Phase: {state.metadata.current_phase.value}",
    ]
    if state.metadata.tech_stack:
        lines.append(f"Tech Stack: {state.metadata.tech_stack}")

    # Inject collective brainstorming insights when available
    ba = state.brainstorming_artifacts
    if ba.collective_consensus:
        lines.append("\n## Collective Brainstorming Insights")
        consensus = ba.collective_consensus
        if len(consensus) > 2000:
            consensus = consensus[:2000] + "\n...[truncated]"
        lines.append(consensus)
        if ba.agreed_tech_stack:
            lines.append(f"\nAgreed Tech Stack: {ba.agreed_tech_stack}")
        if ba.critical_decisions:
            lines.append(f"Critical Decisions: {ba.critical_decisions}")
        if ba.early_risks:
            lines.append(f"Early Risks: {ba.early_risks}")

    if state.planning_artifacts.requirements:
        # Truncate large requirements to save tokens
        reqs = state.planning_artifacts.requirements
        if len(reqs) > 2000:
            reqs = reqs[:2000] + "\n...[truncated]"
        lines.append(f"\n--- Requirements ---\n{reqs}")
    if state.planning_artifacts.complexity_score:
        lines.append(f"Complexity Score: {state.planning_artifacts.complexity_score}/100")

    # Inject cross-run memory context when available
    if state.memory_context and not state.memory_context.is_empty():
        memory_section = state.memory_context.to_prompt_section()
        if memory_section:
            lines.append(f"\n{memory_section}")

    # Inject evaluator feedback when dev agents are re-running after a failed evaluation
    if state.evaluator_score and not state.evaluator_score.passed:
        lines.append(f"\n{state.evaluator_score.to_dev_feedback()}")

    return "\n".join(lines)


def _safe_parse_list(value: Any, item_key: Optional[str] = None) -> List[Any]:
    """Safely parse a value that should be a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if item_key and item_key in value:
            return _safe_parse_list(value[item_key])
        return list(value.values())
    return []


# ============================================================================
# 1. Planning Agent
# ============================================================================

PLANNING_SYSTEM = """You are the Planning Agent in a multi-agent software development system.

Your ONLY job: analyse the user's project request and produce a structured project plan.

OUTPUT: Respond with a single JSON object (no prose before or after):

{
  "requirements": "<markdown requirements document — comprehensive, 300-800 words>",
  "complexity_score": <integer 1-100>,
  "complexity_factors": ["<factor>", ...],
  "tasks": [
    {
      "task_id": "<T001>",
      "title": "<short title>",
      "description": "<what needs to be done>",
      "phase": "<planning|architecture|frontend|backend|qa|documentation>",
      "estimated_complexity": <1-10>
    }
  ],
  "dependencies": {"<task_id>": ["<depends_on_task_id>", ...], ...},
  "risks": ["<risk description>", ...],
  "tech_stack": {"frontend": "<framework or null>", "backend": "<framework or null>"},
  "summary": "<2-3 sentence executive summary>"
}

Rules:
- complexity_score: 1=trivial script, 50=medium web app, 100=enterprise system
- tasks: minimum 4, maximum 15
- risks: minimum 2 items
- Do NOT design architecture. Do NOT write code.
- Response MUST be valid JSON only."""


def run_planning_agent(state: AgentState, client: Optional[LLMClient] = None) -> StateUpdate:
    """Execute the Planning Agent and return a StateUpdate."""
    client = client or get_client()
    logger.info("[Planning] Starting planning agent")

    context = f"User Request:\n{state.metadata.user_request}"
    if state.metadata.tech_stack:
        context += f"\n\nPreferred Tech Stack: {state.metadata.tech_stack}"

    response = client.call(
        system=PLANNING_SYSTEM,
        messages=[{"role": "user", "content": context}],
        max_tokens=4096,
        temperature=0.3,
    )

    data = client.extract_json(response)
    logger.info(
        f"[Planning] Done. Complexity={data.get('complexity_score')}, "
        f"Tasks={len(data.get('tasks', []))}, "
        f"Model={response.model_used}, Tokens={response.output_tokens}"
    )

    artifacts = PlanningArtifacts(
        requirements=data.get("requirements", ""),
        complexity_score=int(data.get("complexity_score", 50)),
        complexity_factors=_safe_parse_list(data.get("complexity_factors", [])),
        tasks=_safe_parse_list(data.get("tasks", [])),
        dependencies=data.get("dependencies", {}),
        risks=_safe_parse_list(data.get("risks", [])),
        tech_stack=data.get("tech_stack"),
        summary=data.get("summary", ""),
    )

    return StateUpdate(
        planning_artifacts=artifacts,
        current_phase=AgentPhase.ARCHITECTURE,
        message=AgentMessage(
            agent_id="planning_agent",
            role="Planning Agent",
            content=f"Planning complete. {len(artifacts.tasks)} tasks, "
                    f"complexity={artifacts.complexity_score}/100. "
                    f"Model: {response.model_used}",
        ),
    )


# ============================================================================
# 2. Architecture Agent
# ============================================================================

ARCHITECTURE_SYSTEM = """You are the Architecture Agent in a multi-agent software development system.

Your ONLY job: design the system architecture based on the project requirements.

OUTPUT: Respond with a single JSON object only:

{
  "system_design": "<markdown architecture description — 400-800 words>",
  "component_specs": {
    "<ComponentName>": {
      "name": "<ComponentName>",
      "description": "<what it does>",
      "props": {"<propName>": "<type description>"},
      "state": ["<state var>"],
      "api_calls": ["<endpoint>"]
    }
  },
  "api_specs": {
    "<unique_key e.g. todos-list>": {
      "path": "/api/<path>",
      "method": "GET|POST|PUT|DELETE|PATCH",
      "description": "<what it does>",
      "request_schema": {"<field>": "<type>"},
      "response_schema": {"<field>": "<type>"},
      "authentication_required": true|false
    }
  },
  "database_schema": "<markdown ER diagram or table descriptions>",
  "technology_decisions": {
    "frontend_framework": "<name>",
    "backend_framework": "<name>",
    "database": "<name>",
    "rationale": "<why these choices>"
  },
  "summary": "<2-3 sentence summary>"
}

Rules:
- api_specs keys must be unique (use pattern: resource-action e.g. todos-list, todos-create)
- Each api_spec path must start with /
- Do NOT write implementation code. Design only.
- Response MUST be valid JSON only."""


def run_architecture_agent(state: AgentState, client: Optional[LLMClient] = None) -> StateUpdate:
    """Execute the Architecture Agent and return a StateUpdate."""
    client = client or get_client()
    logger.info("[Architecture] Starting architecture agent")

    context = _build_project_context(state)
    if state.planning_artifacts.tasks:
        context += f"\n\n--- Task Breakdown ---\n"
        for t in state.planning_artifacts.tasks[:10]:
            if isinstance(t, dict):
                context += f"- [{t.get('task_id','')}] {t.get('title','')}: {t.get('description','')}\n"

    response = client.call(
        system=ARCHITECTURE_SYSTEM,
        messages=[{"role": "user", "content": context}],
        max_tokens=6144,
        temperature=0.2,
    )

    data = client.extract_json(response)

    # Convert raw dicts to typed ComponentSpec / APIEndpoint
    component_specs: Dict[str, ComponentSpec] = {}
    for name, spec in data.get("component_specs", {}).items():
        if isinstance(spec, dict):
            component_specs[name] = ComponentSpec(
                name=spec.get("name", name),
                description=spec.get("description", ""),
                props=spec.get("props", {}) if isinstance(spec.get("props"), dict) else {},
                state=spec.get("state", []) if isinstance(spec.get("state"), list) else [],
                api_calls=spec.get("api_calls", []),
            )

    api_specs: Dict[str, APIEndpoint] = {}
    for key, ep in data.get("api_specs", {}).items():
        if isinstance(ep, dict):
            method = ep.get("method", "GET").upper()
            if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                method = "GET"
            api_specs[key] = APIEndpoint(
                path=ep.get("path", f"/{key}"),
                method=method,
                description=ep.get("description", ""),
                request_schema=ep.get("request_schema", {}) if isinstance(ep.get("request_schema"), dict) else {},
                response_schema=ep.get("response_schema", {}) if isinstance(ep.get("response_schema"), dict) else {},
                authentication_required=bool(ep.get("authentication_required", False)),
            )

    artifacts = ArchitectureArtifacts(
        system_design=data.get("system_design", ""),
        component_specs=component_specs,
        api_specs=api_specs,
        database_schema=data.get("database_schema", ""),
        technology_decisions=data.get("technology_decisions", {}),
        summary=data.get("summary", ""),
    )

    logger.info(
        f"[Architecture] Done. Components={len(component_specs)}, "
        f"Endpoints={len(api_specs)}, Model={response.model_used}"
    )

    return StateUpdate(
        architecture_artifacts=artifacts,
        current_phase=AgentPhase.FRONTEND,
        message=AgentMessage(
            agent_id="architecture_agent",
            role="Architecture Agent",
            content=f"Architecture designed. {len(component_specs)} components, "
                    f"{len(api_specs)} API endpoints. Model: {response.model_used}",
        ),
    )


# ============================================================================
# 3. Frontend Agent
# ============================================================================

FRONTEND_SYSTEM = """You are the Frontend Development Agent in a multi-agent software development system.

Your ONLY job: implement the frontend code based on architecture specifications.

OUTPUT: Respond with a single JSON object only:

{
  "code_files": {
    "<file_path>": "<full file content as string>",
    ...
  },
  "dependencies": ["<npm package>", ...],
  "api_calls": [
    {"method": "GET|POST|PUT|DELETE|PATCH", "url": "<exact path used in fetch/axios, e.g. /api/todos>"},
    ...
  ],
  "summary": "<what was implemented>"
}

CRITICAL Rules:
- Generate REAL, WORKING code — not placeholders
- Limit to 6 most important files to avoid truncation
- Use TypeScript, React functional components, Tailwind CSS
- API calls must use the endpoints from the architecture spec
- File paths: relative (e.g. src/App.tsx, src/components/TodoList.tsx)
- Keep each file under 80 lines — prioritize clarity over completeness
- In JSON strings: escape backslashes as \\\\, newlines as \\n, quotes as \\"
- api_calls: list EVERY API endpoint your code calls (for contract validation)
- Response MUST be valid, complete JSON — do NOT truncate mid-response"""


def run_frontend_agent(
    state: AgentState,
    client: Optional[LLMClient] = None,
    bug_reports: Optional[List[Dict[str, Any]]] = None,
) -> StateUpdate:
    """Execute the Frontend Development Agent.

    Args:
        bug_reports: If provided (self-healing mode), the agent will fix these bugs
                     instead of generating code from scratch.
    """
    client = client or get_client()
    healing_mode = bool(bug_reports)
    logger.info(f"[Frontend] Starting frontend agent (healing={healing_mode})")

    arch = state.architecture_artifacts
    context = _build_project_context(state)
    context += f"\n\n--- Component Specifications ---\n"
    for name, spec in arch.component_specs.items():
        context += f"\n{name}: {spec.description}\n"
        context += f"  Props: {spec.props}\n"
        context += f"  State: {spec.state}\n"
        context += f"  API calls: {spec.api_calls}\n"

    context += f"\n\n--- API Endpoints ---\n"
    for key, ep in arch.api_specs.items():
        context += f"  {ep.method} {ep.path} — {ep.description}\n"

    if arch.technology_decisions:
        context += f"\n\nTech decisions: {arch.technology_decisions}\n"

    # In self-healing mode: include existing code + bugs to fix
    if healing_mode:
        context += f"\n\n--- EXISTING FRONTEND CODE (must be improved) ---\n"
        for path, content in state.development.frontend.code_files.items():
            snippet = content[:600] + "\n...[truncated]" if len(content) > 600 else content
            context += f"\n### {path}\n```\n{snippet}\n```\n"

        frontend_bugs = _filter_bugs(
            bug_reports,
            severities=["critical"],
            components=["frontend", "react", "ui", "component"],
        )
        context += f"\n\n--- BUGS TO FIX (priority: critical first) ---\n"
        for bug in frontend_bugs[:8]:
            context += (
                f"\n[{bug.get('severity', 'unknown').upper()}] {bug.get('bug_id', '')}: "
                f"{bug.get('description', '')}\n"
                f"  Fix: {bug.get('suggested_fix', '')}\n"
            )
        context += "\nIMPORTANT: Fix ALL critical bugs above. Return the complete improved code.\n"

    response = client.call(
        system=FRONTEND_SYSTEM,
        messages=[{"role": "user", "content": context}],
        max_tokens=6000,
        temperature=0.2,
    )

    data = client.extract_json(response)
    code_files = data.get("code_files", {})
    if not isinstance(code_files, dict):
        code_files = {}

    # Publish API calls to the bus for contract validation
    api_calls = data.get("api_calls", [])
    if isinstance(api_calls, list) and api_calls:
        get_bus().publish("frontend_agent", "frontend.api_calls", api_calls)
        logger.info(f"[Frontend] Published {len(api_calls)} API calls to bus")

    action = "healed" if healing_mode else "implemented"
    logger.info(
        f"[Frontend] Done ({action}). Files={len(code_files)}, Model={response.model_used}"
    )

    artifacts = DevelopmentArtifacts(
        code_files=code_files,
        summary=data.get("summary", ""),
    )

    return StateUpdate(
        development=DevelopmentSection(
            frontend=artifacts,
            backend=state.development.backend,
        ),
        current_phase=AgentPhase.BACKEND,
        message=AgentMessage(
            agent_id="frontend_agent",
            role="Frontend Agent",
            content=f"Frontend {action}. {len(code_files)} files generated. "
                    f"Model: {response.model_used}",
        ),
    )


# ============================================================================
# 4. Backend Agent
# ============================================================================

BACKEND_SYSTEM = """You are the Backend Development Agent in a multi-agent software development system.

Your ONLY job: implement the backend API code based on architecture specifications.

OUTPUT: Respond with a single JSON object only:

{
  "code_files": {
    "<file_path>": "<full file content as string>",
    ...
  },
  "dependencies": ["<pip package>", ...],
  "api_routes": [
    {"method": "GET|POST|PUT|DELETE|PATCH", "path": "<exact path registered in FastAPI, e.g. /api/todos>"},
    ...
  ],
  "summary": "<what was implemented>"
}

CRITICAL Rules:
- Generate REAL, WORKING code — no placeholders
- Limit to 6 most important files to avoid truncation
- Use Python, FastAPI, SQLAlchemy or SQLite directly
- File paths: relative (e.g. main.py, routers/todos.py, models.py)
- Keep each file under 80 lines — prioritize working endpoints over completeness
- In JSON strings: escape backslashes as \\\\, newlines as \\n, quotes as \\"
- api_routes: list EVERY route your code registers (for contract validation)
- Response MUST be valid, complete JSON — do NOT truncate mid-response"""


def run_backend_agent(
    state: AgentState,
    client: Optional[LLMClient] = None,
    bug_reports: Optional[List[Dict[str, Any]]] = None,
) -> StateUpdate:
    """Execute the Backend Development Agent.

    Args:
        bug_reports: If provided (self-healing mode), the agent will fix these bugs
                     instead of generating code from scratch.
    """
    client = client or get_client()
    healing_mode = bool(bug_reports)
    logger.info(f"[Backend] Starting backend agent (healing={healing_mode})")

    arch = state.architecture_artifacts
    context = _build_project_context(state)
    context += f"\n\n--- Database Schema ---\n{arch.database_schema}\n"

    context += f"\n\n--- API Endpoints to Implement ---\n"
    for key, ep in arch.api_specs.items():
        context += (
            f"\n{ep.method} {ep.path} — {ep.description}\n"
            f"  Request:  {ep.request_schema}\n"
            f"  Response: {ep.response_schema}\n"
            f"  Auth required: {ep.authentication_required}\n"
        )

    if arch.technology_decisions:
        context += f"\n\nTech decisions: {arch.technology_decisions}\n"

    # In self-healing mode: include existing code + bugs to fix
    if healing_mode:
        context += f"\n\n--- EXISTING BACKEND CODE (must be improved) ---\n"
        for path, content in state.development.backend.code_files.items():
            snippet = content[:600] + "\n...[truncated]" if len(content) > 600 else content
            context += f"\n### {path}\n```\n{snippet}\n```\n"

        backend_bugs = _filter_bugs(bug_reports, severities=["critical", "high"])
        context += f"\n\n--- BUGS TO FIX (priority: critical first) ---\n"
        for bug in backend_bugs[:8]:
            context += (
                f"\n[{bug.get('severity', 'unknown').upper()}] {bug.get('bug_id', '')}: "
                f"{bug.get('description', '')}\n"
                f"  Fix: {bug.get('suggested_fix', '')}\n"
            )
        context += "\nIMPORTANT: Fix ALL critical bugs above. Return the complete improved code.\n"

    response = client.call(
        system=BACKEND_SYSTEM,
        messages=[{"role": "user", "content": context}],
        max_tokens=6000,
        temperature=0.2,
    )

    data = client.extract_json(response)
    code_files = data.get("code_files", {})
    if not isinstance(code_files, dict):
        code_files = {}

    # Publish API routes to the bus for contract validation
    api_routes = data.get("api_routes", [])
    if isinstance(api_routes, list) and api_routes:
        get_bus().publish("backend_agent", "backend.api_routes", api_routes)
        logger.info(f"[Backend] Published {len(api_routes)} API routes to bus")

    action = "healed" if healing_mode else "implemented"
    logger.info(
        f"[Backend] Done ({action}). Files={len(code_files)}, Model={response.model_used}"
    )

    artifacts = DevelopmentArtifacts(
        code_files=code_files,
        summary=data.get("summary", ""),
    )

    return StateUpdate(
        development=DevelopmentSection(
            frontend=state.development.frontend,
            backend=artifacts,
        ),
        current_phase=AgentPhase.QA,
        message=AgentMessage(
            agent_id="backend_agent",
            role="Backend Agent",
            content=f"Backend {action}. {len(code_files)} files generated. "
                    f"Model: {response.model_used}",
        ),
    )


# ============================================================================
# 5. QA Agent
# ============================================================================

QA_SYSTEM = """You are the QA Agent in a multi-agent software development system.

Your ONLY job: review the generated frontend and backend code, identify issues,
and produce a quality assessment with test cases.

OUTPUT: Respond with a single JSON object only:

{
  "test_results": {
    "total": <int>,
    "passed": <int>,
    "failed": <int>,
    "coverage": <float 0-100>
  },
  "test_cases": [
    {
      "test_id": "<id>",
      "name": "<test name>",
      "target": "frontend|backend",
      "description": "<what is tested>",
      "expected": "<expected behaviour>",
      "status": "passed|failed|skipped"
    }
  ],
  "bug_reports": [
    {
      "bug_id": "<id>",
      "severity": "critical|high|medium|low",
      "component": "<file or component name>",
      "description": "<specific bug description>",
      "suggested_fix": "<concrete fix instructions>"
    }
  ],
  "error_analysis": {
    "root_causes": ["<root cause>"],
    "affected_agents": ["frontend", "backend"],
    "restart_needed": <true if critical bugs exist that can be fixed by re-running dev agents, false otherwise>
  },
  "overall_quality": "excellent|good|acceptable|needs_work",
  "summary": "<quality summary>"
}

Rules:
- Be realistic — simulate test execution based on code review
- If code is missing or empty, report that as critical bugs
- coverage should reflect your best estimate from the code
- Set restart_needed=true ONLY if there are critical bugs that the dev agents could fix
- Set restart_needed=false if quality is already acceptable (>70% pass rate, no critical bugs)
- affected_agents: list which of ["frontend", "backend"] need to be re-run
- Limit to 10 test cases and 8 bug reports to avoid truncation
- Response MUST be valid JSON only."""


def run_qa_agent(state: AgentState, client: Optional[LLMClient] = None) -> StateUpdate:
    """Execute the QA Agent.

    Runs real code execution (pytest + tsc) first, then asks the LLM to
    analyse the code *and* the real execution results to produce a final
    quality report.
    """
    client = client or get_client()
    logger.info("[QA] Starting QA agent")

    # ------------------------------------------------------------------
    # 1. Real code execution (best-effort — never blocks the pipeline)
    # ------------------------------------------------------------------
    backend_real: Optional[object] = None
    frontend_real: Optional[object] = None

    if state.development.backend.code_files:
        logger.info("[QA] Running real backend tests (pytest)")
        try:
            backend_real = BackendCodeRunner().run(state.development.backend.code_files)
            logger.info(f"[QA] Backend real result: {backend_real.as_summary()}")
        except Exception as exc:
            logger.warning(f"[QA] BackendCodeRunner failed: {exc}")

    if state.development.frontend.code_files:
        logger.info("[QA] Running real frontend type check (tsc)")
        try:
            frontend_real = FrontendCodeRunner().run(state.development.frontend.code_files)
            logger.info(f"[QA] Frontend real result: {frontend_real.as_summary()}")
        except Exception as exc:
            logger.warning(f"[QA] FrontendCodeRunner failed: {exc}")

    # ------------------------------------------------------------------
    # 2. Build LLM context (code samples + real execution results)
    # ------------------------------------------------------------------
    context = _build_project_context(state)

    # Include code samples (truncated to fit context)
    frontend_files = list(state.development.frontend.code_files.items())
    backend_files  = list(state.development.backend.code_files.items())

    context += f"\n\n--- Frontend Code ({len(frontend_files)} files) ---\n"
    for path, content in frontend_files[:5]:  # show first 5 files
        snippet = content[:800] + "\n...[truncated]" if len(content) > 800 else content
        context += f"\n### {path}\n```\n{snippet}\n```\n"

    context += f"\n\n--- Backend Code ({len(backend_files)} files) ---\n"
    for path, content in backend_files[:5]:
        snippet = content[:800] + "\n...[truncated]" if len(content) > 800 else content
        context += f"\n### {path}\n```\n{snippet}\n```\n"

    # Inject real execution results so LLM can factor them in
    context += "\n\n--- REAL CODE EXECUTION RESULTS ---\n"
    if backend_real is not None:
        context += f"Backend pytest: {backend_real.as_summary()}\n"
        if backend_real.errors:
            context += "Backend errors:\n"
            for err in backend_real.errors[:5]:
                context += f"  {err}\n"
    else:
        context += "Backend pytest: not run (no code or runner unavailable)\n"

    if frontend_real is not None:
        context += f"Frontend tsc: {frontend_real.as_summary()}\n"
        if frontend_real.errors:
            context += "TypeScript errors:\n"
            for err in frontend_real.errors[:5]:
                context += f"  {err}\n"
    else:
        context += "Frontend tsc: not run (no code or runner unavailable)\n"

    context += (
        "\nIMPORTANT: The test_results in your JSON response MUST reflect the "
        "REAL execution results above, not guesses based on code review alone.\n"
    )

    # ------------------------------------------------------------------
    # 3. LLM quality analysis
    # ------------------------------------------------------------------
    response = client.call(
        system=QA_SYSTEM,
        messages=[{"role": "user", "content": context}],
        max_tokens=4096,
        temperature=0.3,
    )

    data = client.extract_json(response)
    test_results = data.get("test_results", {"total": 0, "passed": 0, "failed": 0, "coverage": 0})

    # ------------------------------------------------------------------
    # 4. Merge real results into test_results if they are more accurate
    # ------------------------------------------------------------------
    if backend_real is not None and backend_real.total > 0:
        # Prefer real numbers over LLM estimates for backend
        llm_total = test_results.get("total", 0)
        if llm_total == 0 or backend_real.total > llm_total:
            test_results["total"] = backend_real.total
            test_results["passed"] = backend_real.passed
            test_results["failed"] = backend_real.failed
            test_results["real_backend_result"] = backend_real.as_summary()

    if frontend_real is not None:
        test_results["real_frontend_result"] = frontend_real.as_summary()
        if not frontend_real.success and frontend_real.failed > 0:
            # TypeScript errors are real failures — reflect in counts
            test_results["failed"] = test_results.get("failed", 0) + frontend_real.failed

    logger.info(
        f"[QA] Done. Tests={test_results.get('total')}, "
        f"Passed={test_results.get('passed')}, "
        f"Coverage={test_results.get('coverage')}%, "
        f"Quality={data.get('overall_quality')}, "
        f"Model={response.model_used}"
    )

    artifacts = TestingArtifacts(
        test_results=test_results,
        bug_reports=data.get("bug_reports", []),
        error_analysis=data.get("error_analysis"),
        summary=data.get("summary", ""),
    )

    # Determine if we need to restart any agents based on critical bugs
    critical_bugs = [
        b for b in data.get("bug_reports", [])
        if isinstance(b, dict) and b.get("severity") == "critical"
    ]
    restart_needed = data.get("error_analysis", {}).get("restart_needed", False)

    if critical_bugs and restart_needed:
        logger.warning(f"[QA] {len(critical_bugs)} critical bugs found, restart may be needed")

    return StateUpdate(
        testing_artifacts=artifacts,
        current_phase=AgentPhase.DOCUMENTATION,
        message=AgentMessage(
            agent_id="qa_agent",
            role="QA Agent",
            content=f"QA complete. {test_results.get('passed')}/{test_results.get('total')} tests passed, "
                    f"coverage={test_results.get('coverage')}%, "
                    f"{len(data.get('bug_reports', []))} bugs found. "
                    f"Model: {response.model_used}",
        ),
    )


# ============================================================================
# 6. Documentation Agent
# ============================================================================

DOCUMENTATION_SYSTEM = """You are the Documentation Agent in a multi-agent software development system.

Your ONLY job: create documentation for the project.

OUTPUT: Respond with a single JSON object only:

{
  "readme": "<README.md content in markdown — max 400 words>",
  "api_docs": "<API docs — list each endpoint with method, path, description>",
  "architecture_docs": "<architecture overview — max 200 words>",
  "deployment_guide": "<setup steps — max 200 words>",
  "summary": "<one sentence summary>"
}

CRITICAL Rules:
- Keep each field concise (under 400 words) to avoid truncation
- readme: description, features list, tech stack, quick start
- In JSON strings: escape backslashes as \\\\, newlines as \\n, quotes as \\"
- Response MUST be valid, complete JSON — do NOT truncate mid-response"""


def run_documentation_agent(state: AgentState, client: Optional[LLMClient] = None) -> StateUpdate:
    """Execute the Documentation Agent."""
    client = client or get_client()
    logger.info("[Documentation] Starting documentation agent")

    context = _build_project_context(state)
    context += f"\n\nSystem Design Summary:\n{state.architecture_artifacts.system_design[:1000]}\n"

    context += f"\n\nAPI Endpoints:\n"
    for key, ep in state.architecture_artifacts.api_specs.items():
        context += f"  {ep.method} {ep.path} — {ep.description}\n"

    context += f"\n\nFrontend Files Generated: {list(state.development.frontend.code_files.keys())}\n"
    context += f"Backend Files Generated:  {list(state.development.backend.code_files.keys())}\n"

    tr = state.testing_artifacts.test_results or {}
    context += (
        f"\n\nTest Results: {tr.get('passed', 0)}/{tr.get('total', 0)} passed, "
        f"coverage={tr.get('coverage', 0)}%\n"
    )

    response = client.call(
        system=DOCUMENTATION_SYSTEM,
        messages=[{"role": "user", "content": context}],
        max_tokens=6144,
        temperature=0.3,
    )

    data = client.extract_json(response)

    logger.info(
        f"[Documentation] Done. Model={response.model_used}"
    )

    artifacts = DocumentationArtifacts(
        readme=data.get("readme", ""),
        api_docs=data.get("api_docs", ""),
        architecture_docs=data.get("architecture_docs", ""),
        deployment_guide=data.get("deployment_guide", ""),
        summary=data.get("summary", ""),
    )

    return StateUpdate(
        documentation_artifacts=artifacts,
        current_phase=AgentPhase.COMPLETE,
        is_complete=True,
        message=AgentMessage(
            agent_id="documentation_agent",
            role="Documentation Agent",
            content=f"Documentation complete. README, API docs, architecture docs, "
                    f"and deployment guide generated. Model: {response.model_used}",
        ),
    )


# ============================================================================
# 0. Brainstorming Agents
# ============================================================================

BRAINSTORMING_SYSTEM_PROMPTS: Dict[str, str] = {
    "planning": """You are a senior product manager performing a preliminary brainstorming analysis.

Your job: examine the project request and produce a DESIGN SKETCH (not implementation) from a
requirements and planning perspective. Focus on scope, ambiguities, priorities, and constraints.

OUTPUT: Respond with a single JSON object only:
{
  "agent_role": "planning",
  "domain_concerns": ["<concern 1>", "<concern 2>", "..."],
  "preliminary_design": {
    "scope_boundaries": "<what is in vs out of scope>",
    "ambiguities": "<unclear requirements needing clarification>",
    "mvp_features": "<minimum viable set of features>",
    "non_functional_requirements": "<performance, security, scalability notes>"
  },
  "recommended_approaches": ["<approach 1>", "..."],
  "risks_and_challenges": ["<risk 1>", "..."],
  "dependencies_on_others": ["<what you need from architecture/frontend/backend/qa/docs>"]
}

Rules:
- domain_concerns: minimum 2, maximum 8 items
- Do NOT generate code — design sketches only
- Response MUST be valid, complete JSON""",

    "architecture": """You are a senior solutions architect performing a preliminary brainstorming analysis.

Your job: examine the project request and produce a DESIGN SKETCH (not implementation) from a
system architecture perspective. Focus on patterns, tech stack, data flow, and scalability.

OUTPUT: Respond with a single JSON object only:
{
  "agent_role": "architecture",
  "domain_concerns": ["<concern 1>", "<concern 2>", "..."],
  "preliminary_design": {
    "architecture_pattern": "<recommended pattern: monolith/microservices/serverless/etc.>",
    "tech_stack_candidates": "<frontend + backend + DB recommendations with rationale>",
    "data_flow": "<high-level data flow description>",
    "component_boundaries": "<key system components and their responsibilities>",
    "integration_points": "<external services, APIs, or systems>"
  },
  "recommended_approaches": ["<approach 1>", "..."],
  "risks_and_challenges": ["<risk 1>", "..."],
  "dependencies_on_others": ["<what you need from planning/frontend/backend/qa>"]
}

Rules:
- domain_concerns: minimum 2, maximum 8 items
- Do NOT generate code — design sketches only
- Response MUST be valid, complete JSON""",

    "frontend": """You are a senior frontend engineer performing a preliminary brainstorming analysis.

Your job: examine the project request and produce a DESIGN SKETCH (not implementation) from a
UI/UX and frontend architecture perspective. Focus on component structure, state management, and API integration.

OUTPUT: Respond with a single JSON object only:
{
  "agent_role": "frontend",
  "domain_concerns": ["<concern 1>", "<concern 2>", "..."],
  "preliminary_design": {
    "ui_framework": "<recommended framework and why>",
    "component_hierarchy": "<top-level component breakdown>",
    "state_management": "<recommended state management approach>",
    "routing_structure": "<page/route hierarchy>",
    "api_integration_pattern": "<how frontend will consume backend APIs>"
  },
  "recommended_approaches": ["<approach 1>", "..."],
  "risks_and_challenges": ["<risk 1>", "..."],
  "dependencies_on_others": ["<what you need from architecture/backend/qa>"]
}

Rules:
- domain_concerns: minimum 2, maximum 8 items
- Do NOT generate code — design sketches only
- Response MUST be valid, complete JSON""",

    "backend": """You are a senior backend engineer performing a preliminary brainstorming analysis.

Your job: examine the project request and produce a DESIGN SKETCH (not implementation) from a
backend and API design perspective. Focus on data models, API contracts, auth, and scalability.

OUTPUT: Respond with a single JSON object only:
{
  "agent_role": "backend",
  "domain_concerns": ["<concern 1>", "<concern 2>", "..."],
  "preliminary_design": {
    "api_style": "<REST/GraphQL/gRPC and rationale>",
    "data_model_sketch": "<key entities and relationships>",
    "auth_strategy": "<authentication and authorization approach>",
    "business_logic_structure": "<services, repositories, use cases>",
    "performance_considerations": "<caching, indexing, bottlenecks>"
  },
  "recommended_approaches": ["<approach 1>", "..."],
  "risks_and_challenges": ["<risk 1>", "..."],
  "dependencies_on_others": ["<what you need from architecture/frontend/qa>"]
}

Rules:
- domain_concerns: minimum 2, maximum 8 items
- Do NOT generate code — design sketches only
- Response MUST be valid, complete JSON""",

    "qa": """You are a senior QA engineer performing a preliminary brainstorming analysis.

Your job: examine the project request and produce a DESIGN SKETCH (not implementation) from a
testing and quality assurance perspective. Focus on test strategy, testability, and quality gates.

OUTPUT: Respond with a single JSON object only:
{
  "agent_role": "qa",
  "domain_concerns": ["<concern 1>", "<concern 2>", "..."],
  "preliminary_design": {
    "test_pyramid": "<unit/integration/e2e ratio recommendation>",
    "critical_paths": "<which flows require 100% coverage>",
    "testability_concerns": "<design choices that affect testability>",
    "ci_pipeline": "<recommended CI/CD quality gates>",
    "performance_and_security_testing": "<non-functional test needs>"
  },
  "recommended_approaches": ["<approach 1>", "..."],
  "risks_and_challenges": ["<risk 1>", "..."],
  "dependencies_on_others": ["<what you need from architecture/frontend/backend>"]
}

Rules:
- domain_concerns: minimum 2, maximum 8 items
- Do NOT generate code — design sketches only
- Response MUST be valid, complete JSON""",

    "documentation": """You are a senior technical writer performing a preliminary brainstorming analysis.

Your job: examine the project request and produce a DESIGN SKETCH (not implementation) from a
documentation perspective. Focus on audience, doc types, and maintenance strategy.

OUTPUT: Respond with a single JSON object only:
{
  "agent_role": "documentation",
  "domain_concerns": ["<concern 1>", "<concern 2>", "..."],
  "preliminary_design": {
    "target_audience": "<developers, end users, operators — who reads the docs>",
    "required_doc_types": "<README, API reference, ADRs, runbooks, etc.>",
    "doc_as_code": "<feasibility of docs-as-code approach>",
    "onboarding_sequence": "<recommended sequence for new developers>",
    "versioning_strategy": "<how to keep docs in sync with code>"
  },
  "recommended_approaches": ["<approach 1>", "..."],
  "risks_and_challenges": ["<risk 1>", "..."],
  "dependencies_on_others": ["<what you need from planning/architecture/frontend/backend>"]
}

Rules:
- domain_concerns: minimum 2, maximum 8 items
- Do NOT generate code — design sketches only
- Response MUST be valid, complete JSON""",
}

BRAINSTORMING_SYNTHESIS_SYSTEM = """You are a senior engineering lead performing synthesis of team brainstorming perspectives.

You have received preliminary design analyses from 6 domain experts (planning, architecture,
frontend, backend, qa, documentation). Your job: synthesize these into a unified collective
consensus that will guide the entire multi-agent workflow.

OUTPUT: Respond with a single JSON object only:
{
  "collective_consensus": "<500-1000 word synthesis covering: agreed decisions, key trade-offs, cross-cutting concerns, and what each agent should know before starting their main task>",
  "agreed_tech_stack": {
    "frontend": "<framework>",
    "backend": "<framework>",
    "database": "<technology>",
    "auth": "<mechanism>",
    "deployment": "<target>"
  },
  "critical_decisions": [
    "<decision 1 that requires explicit attention during implementation>",
    "<decision 2>",
    "..."
  ],
  "early_risks": [
    "<risk identified by multiple perspectives>",
    "..."
  ]
}

Rules:
- collective_consensus: 200 words minimum, captures cross-cutting themes
- agreed_tech_stack: include at minimum 'frontend' and 'backend' keys
- critical_decisions: minimum 2 items
- Resolve conflicts between perspectives pragmatically — choose the most appropriate approach
- Response MUST be valid, complete JSON"""


def run_brainstorming_agent(
    perspective_role: str,
    state: AgentState,
    client: Optional[LLMClient] = None,
) -> StateUpdate:
    """
    Execute a brainstorming agent for a specific domain perspective.

    Args:
        perspective_role: One of planning, architecture, frontend, backend, qa, documentation
        state: Current project state
        client: Optional LLM client (uses singleton if omitted)

    Returns:
        StateUpdate with brainstorming_artifacts containing the new perspective
    """
    if client is None:
        client = get_client()

    system_prompt = BRAINSTORMING_SYSTEM_PROMPTS.get(perspective_role)
    if system_prompt is None:
        raise ValueError(f"Unknown brainstorming role: '{perspective_role}'")

    user_msg = f"Project Request: {state.metadata.user_request}"
    if state.metadata.tech_stack:
        user_msg += f"\nTech Stack Hint: {state.metadata.tech_stack}"

    logger.info(f"[Brainstorming] Running {perspective_role} perspective")

    response: LLMResponse = client.complete(
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
        max_tokens=2048,
    )

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    data = json.loads(raw)

    perspective = BrainstormingPerspective(
        agent_role=perspective_role,
        domain_concerns=data.get("domain_concerns", []),
        preliminary_design=data.get("preliminary_design", {}),
        recommended_approaches=data.get("recommended_approaches", []),
        risks_and_challenges=data.get("risks_and_challenges", []),
        dependencies_on_others=data.get("dependencies_on_others", []),
    )

    # Return update with this single perspective; caller merges into state
    existing = state.brainstorming_artifacts.perspectives.copy()
    existing[perspective_role] = perspective
    updated_artifacts = BrainstormingArtifacts(
        perspectives=existing,
        collective_consensus=state.brainstorming_artifacts.collective_consensus,
        agreed_tech_stack=state.brainstorming_artifacts.agreed_tech_stack,
        critical_decisions=state.brainstorming_artifacts.critical_decisions,
        early_risks=state.brainstorming_artifacts.early_risks,
    )

    logger.info(
        f"[Brainstorming] {perspective_role} complete. "
        f"Concerns: {len(perspective.domain_concerns)}, "
        f"Approaches: {len(perspective.recommended_approaches)}. "
        f"Model: {response.model_used}"
    )

    return StateUpdate(
        brainstorming_artifacts=updated_artifacts,
        message=AgentMessage(
            agent_id=f"brainstorming_{perspective_role}",
            role=f"Brainstorming Agent ({perspective_role})",
            content=(
                f"Brainstorming ({perspective_role}) complete: "
                f"{len(perspective.domain_concerns)} concerns, "
                f"{len(perspective.recommended_approaches)} approaches identified."
            ),
        ),
    )


def run_synthesis_agent(
    state: AgentState,
    client: Optional[LLMClient] = None,
) -> StateUpdate:
    """
    Synthesize all brainstorming perspectives into collective consensus.

    Args:
        state: Current project state (must have brainstorming_artifacts.perspectives populated)
        client: Optional LLM client (uses singleton if omitted)

    Returns:
        StateUpdate with completed BrainstormingArtifacts
    """
    if client is None:
        client = get_client()

    perspectives = state.brainstorming_artifacts.perspectives
    perspectives_json = json.dumps(
        {role: p.model_dump() for role, p in perspectives.items()},
        indent=2,
    )

    user_msg = (
        f"Project Request: {state.metadata.user_request}\n\n"
        f"Brainstorming Perspectives:\n{perspectives_json}"
    )

    logger.info(f"[Brainstorming] Running synthesis over {len(perspectives)} perspectives")

    response: LLMResponse = client.complete(
        system=BRAINSTORMING_SYNTHESIS_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
        max_tokens=3000,
    )

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    data = json.loads(raw)

    updated_artifacts = BrainstormingArtifacts(
        perspectives=perspectives,
        collective_consensus=data.get("collective_consensus", ""),
        agreed_tech_stack=data.get("agreed_tech_stack"),
        critical_decisions=data.get("critical_decisions", []),
        early_risks=data.get("early_risks", []),
        completed_at=datetime.now(timezone.utc),
    )

    logger.info(
        f"[Brainstorming] Synthesis complete. "
        f"Tech stack agreed: {updated_artifacts.agreed_tech_stack}. "
        f"Critical decisions: {len(updated_artifacts.critical_decisions)}. "
        f"Model: {response.model_used}"
    )

    return StateUpdate(
        brainstorming_artifacts=updated_artifacts,
        message=AgentMessage(
            agent_id="brainstorming_synthesis",
            role="Brainstorming Synthesis Agent",
            content=(
                f"Brainstorming synthesis complete: "
                f"{len(perspectives)} perspectives consolidated, "
                f"{len(updated_artifacts.critical_decisions)} critical decisions identified."
            ),
        ),
    )


# ============================================================================
# Dispatcher
# ============================================================================

AGENT_RUNNERS = {
    # Brainstorming agents
    "brainstorming_planning":       lambda state, client=None, **kw: run_brainstorming_agent("planning", state, client),
    "brainstorming_architecture":   lambda state, client=None, **kw: run_brainstorming_agent("architecture", state, client),
    "brainstorming_frontend":       lambda state, client=None, **kw: run_brainstorming_agent("frontend", state, client),
    "brainstorming_backend":        lambda state, client=None, **kw: run_brainstorming_agent("backend", state, client),
    "brainstorming_qa":             lambda state, client=None, **kw: run_brainstorming_agent("qa", state, client),
    "brainstorming_documentation":  lambda state, client=None, **kw: run_brainstorming_agent("documentation", state, client),
    "brainstorming_synthesis":      run_synthesis_agent,
    # Main workflow agents
    "planning":      run_planning_agent,
    "architecture":  run_architecture_agent,
    "frontend":      run_frontend_agent,
    "backend":       run_backend_agent,
    "qa":            run_qa_agent,
    "documentation": run_documentation_agent,
}


def execute_agent(
    agent_id: str,
    state: AgentState,
    client: Optional[LLMClient] = None,
    bug_reports: Optional[List[Dict[str, Any]]] = None,
) -> StateUpdate:
    """
    Dispatch to the correct agent runner.

    Args:
        agent_id: One of brainstorming_*, planning, architecture, frontend, backend, qa, documentation
        state: Current project state
        client: Optional LLM client (uses singleton if omitted)
        bug_reports: Optional list of bug dicts from QA — activates self-healing mode
                     for frontend and backend agents.

    Returns:
        StateUpdate to be applied by the orchestrator

    Raises:
        ValueError: If agent_id is unknown
        RuntimeError: If the LLM call fails after all retries
    """
    runner = AGENT_RUNNERS.get(agent_id)
    if runner is None:
        raise ValueError(
            f"Unknown agent_id: '{agent_id}'. "
            f"Known agents: {list(AGENT_RUNNERS.keys())}"
        )
    # Pass bug_reports only to agents that support self-healing
    if agent_id in ("frontend", "backend") and bug_reports:
        return runner(state, client, bug_reports)
    return runner(state, client)


# ============================================================================
# Observer Agents — extract structured facts after each phase
# ============================================================================

_OBSERVER_SYSTEM = """You are an Observer Agent in a multi-agent AI system.
Your job: analyse the completed work for this phase and extract structured,
reusable knowledge facts for future runs.

OUTPUT: Respond with a single JSON object (no prose):

{
  "facts": [
    {
      "category": "<bug_pattern|success_pattern|tech_decision|quality_metric>",
      "content": "<concise, actionable fact — 1-3 sentences max>",
      "outcome": "<what happened — fixed_by/used_in/avoided_by>",
      "severity": "<critical|high|medium|low or null>"
    }
  ],
  "summary": "<2-3 sentence summary of key observations>"
}

Rules:
- Extract ONLY non-obvious facts that would genuinely help future runs
- bug_pattern: concrete issues found, with enough detail to recognize the pattern again
- success_pattern: approaches that worked particularly well
- tech_decision: important technology choices and their rationale
- quality_metric: coverage %, healing rounds used, token cost indicators
- Maximum 8 facts per observer
- severity only for bug_pattern facts
"""


def run_observer_agent(
    phase: str,
    observer_type: str,
    context: str,
    project_type: str,
    tech_stack: list[str],
    project_id: str,
    client: Optional[LLMClient] = None,
) -> "ObserverOutput":
    """Run a single Observer Agent to extract facts from a completed phase.

    Args:
        phase: Workflow phase that just completed (e.g. "frontend+backend").
        observer_type: "technical" | "quality" | "metrics"
        context: Relevant phase artifacts serialized as text.
        project_type: Project category for storage metadata.
        tech_stack: Technologies used.
        project_id: Source project ID.
        client: Optional LLM client.

    Returns:
        ObserverOutput with extracted MemoryFact objects.
    """
    from memory.models import MemoryFact, ObserverOutput
    from config.constants import OBSERVER_MAX_TOKENS, OBSERVER_TEMPERATURE

    if client is None:
        client = get_client()

    focus_map = {
        "technical": "technical decisions, architecture choices, and technology rationale",
        "quality": "bugs found, their root causes, how they were resolved, and recurring patterns",
        "metrics": "quality metrics (coverage, healing rounds, error rates) and performance indicators",
    }
    focus = focus_map.get(observer_type, "general observations")

    user_msg = (
        f"Phase: {phase}\n"
        f"Observer Focus: {focus}\n\n"
        f"=== Phase Artifacts ===\n{context[:4000]}"
    )

    try:
        resp = client.call(
            system=_OBSERVER_SYSTEM,
            user=user_msg,
            max_tokens=OBSERVER_MAX_TOKENS,
            temperature=OBSERVER_TEMPERATURE,
        )
        data = json.loads(resp.content) if isinstance(resp.content, str) else resp.content
    except Exception as e:
        logger.warning("Observer agent (%s/%s) failed: %s", phase, observer_type, e)
        return ObserverOutput(observer_type=observer_type, phase=phase)

    facts = []
    for raw in data.get("facts", []):
        if not isinstance(raw, dict) or not raw.get("content"):
            continue
        try:
            facts.append(MemoryFact(
                category=raw.get("category", "quality_metric"),
                project_type=project_type,
                tech_stack=tech_stack,
                phase=phase,
                content=raw["content"],
                outcome=raw.get("outcome", ""),
                severity=raw.get("severity"),
                project_id=project_id,
            ))
        except Exception as e:
            logger.debug("Skipping malformed fact: %s", e)

    return ObserverOutput(
        observer_type=observer_type,
        phase=phase,
        facts=facts,
        summary=data.get("summary", ""),
    )


def run_observer_agents_parallel(
    phase: str,
    state: AgentState,
    client: Optional[LLMClient] = None,
) -> list["ObserverOutput"]:
    """Run 3 Observer Agents in parallel after a phase completes.

    Args:
        phase: Phase name that just completed.
        state: Current AgentState (used for context extraction).
        client: Optional LLM client.

    Returns:
        List of 3 ObserverOutput objects (one per observer type).
    """
    from memory.models import ObserverOutput

    project_id = state.metadata.project_id
    project_type = _infer_project_type(state)
    tech_stack = _extract_tech_stack(state)
    context = _build_observer_context(phase, state)

    observer_types = ["technical", "quality", "metrics"]
    outputs: list[ObserverOutput] = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                run_observer_agent,
                phase, ot, context, project_type, tech_stack, project_id, client
            ): ot
            for ot in observer_types
        }
        for future in as_completed(futures):
            ot = futures[future]
            try:
                outputs.append(future.result())
            except Exception as e:
                logger.warning("Observer %s failed: %s", ot, e)
                outputs.append(ObserverOutput(observer_type=ot, phase=phase))

    total_facts = sum(len(o.facts) for o in outputs)
    logger.info("Observer agents (%s): extracted %d facts", phase, total_facts)
    return outputs


def _infer_project_type(state: AgentState) -> str:
    """Infer a project type label from the user request."""
    req = state.metadata.user_request.lower()
    if any(w in req for w in ["dashboard", "admin", "cms"]):
        return "admin-dashboard"
    if any(w in req for w in ["ecommerce", "shop", "store", "cart"]):
        return "ecommerce"
    if any(w in req for w in ["chat", "messaging", "realtime"]):
        return "realtime-app"
    if any(w in req for w in ["api", "rest", "graphql", "microservice"]):
        return "api-service"
    if any(w in req for w in ["game", "canvas", "webgl"]):
        return "game"
    return "fullstack-web"


def _extract_tech_stack(state: AgentState) -> list[str]:
    """Extract tech stack list from state."""
    stack = []
    if state.metadata.tech_stack:
        stack.extend(state.metadata.tech_stack.values())
    if state.brainstorming_artifacts.agreed_tech_stack:
        agreed = state.brainstorming_artifacts.agreed_tech_stack
        if isinstance(agreed, dict):
            stack.extend(str(v) for v in agreed.values())
        elif isinstance(agreed, list):
            stack.extend(str(v) for v in agreed)
    return [s.lower() for s in stack if s]


def _build_observer_context(phase: str, state: AgentState) -> str:
    """Build a compact context string for Observer Agents from phase artifacts."""
    parts = []

    if "frontend" in phase or "backend" in phase or "dev" in phase:
        fe = state.development.frontend
        be = state.development.backend
        if fe.code_files:
            parts.append(f"Frontend files: {list(fe.code_files.keys())}")
            parts.append(f"Frontend summary: {fe.summary or 'N/A'}")
        if be.code_files:
            parts.append(f"Backend files: {list(be.code_files.keys())}")
            parts.append(f"Backend summary: {be.summary or 'N/A'}")

    if "qa" in phase or "testing" in phase:
        ta = state.testing_artifacts
        if ta.test_results:
            parts.append(f"Test results: {json.dumps(ta.test_results)}")
        if ta.bug_reports:
            parts.append(f"Bug reports ({len(ta.bug_reports)}): {json.dumps(ta.bug_reports[:5])}")
        if ta.error_analysis:
            parts.append(f"Error analysis: {json.dumps(ta.error_analysis)}")

    if "architecture" in phase:
        arch = state.architecture_artifacts
        if arch.system_design:
            parts.append(f"Architecture: {arch.system_design[:500]}")
        if arch.technology_decisions:
            parts.append(f"Tech decisions: {arch.technology_decisions}")

    if not parts:
        parts.append(f"Phase {phase} completed.")
        parts.append(f"User request: {state.metadata.user_request}")

    return "\n".join(parts)


# ============================================================================
# Search Agents — retrieve relevant context before a workflow run
# ============================================================================

_SEARCH_SYSTEM = """You are a Search Agent in a multi-agent AI system.
Your job: given stored memory facts, synthesise the most relevant insights
for the upcoming project run.

OUTPUT: Respond with a single JSON object (no prose):

{
  "synthesis": "<2-4 sentence synthesis of key insights relevant to this project>",
  "key_points": ["<point 1>", "<point 2>", "..."]
}

Focus only on actionable insights — skip obvious or generic advice.
Maximum 6 key_points.
"""


def run_search_agents_parallel(
    user_request: str,
    project_type: str,
    tech_stack: list[str],
    client: Optional[LLMClient] = None,
) -> "MemoryContext":
    """Run 3 Search Agents in parallel to build pre-run MemoryContext.

    Each agent queries the memory backend for a specific category and uses
    the LLM to synthesise a focused summary. The final MemoryContext is built
    from the backend search results (synthesis is logged for debugging only).

    Args:
        user_request: The user's project description.
        project_type: Inferred project category.
        tech_stack: Target technologies.
        client: Optional LLM client.

    Returns:
        MemoryContext ready to inject into state.
    """
    from memory.memory_manager import get_memory_manager
    from config.constants import MEMORY_SEARCH_MAX_TOKENS, MEMORY_SEARCH_TEMPERATURE

    manager = get_memory_manager()
    if client is None:
        client = get_client()

    def _search_and_summarise(focus: str, category: str) -> str:
        """Search memory and return an LLM synthesis string (for logging)."""
        facts = manager.search(
            category=category,
            project_type=project_type,
            tech_stack=tech_stack,
            limit=15,
        )
        if not facts:
            return ""
        facts_text = "\n".join(
            f"[{f.category}/{f.severity or 'info'}] {f.content} → {f.outcome}"
            for f in facts[:10]
        )
        user_msg = (
            f"Project: {user_request[:300]}\n"
            f"Tech stack: {tech_stack}\n"
            f"Search focus: {focus}\n\n"
            f"=== Retrieved Facts ===\n{facts_text}"
        )
        try:
            resp = client.call(
                system=_SEARCH_SYSTEM,
                user=user_msg,
                max_tokens=MEMORY_SEARCH_MAX_TOKENS,
                temperature=MEMORY_SEARCH_TEMPERATURE,
            )
            data = json.loads(resp.content) if isinstance(resp.content, str) else resp.content
            return data.get("synthesis", "")
        except Exception as e:
            logger.warning("Search agent (%s) LLM call failed: %s", focus, e)
            return ""

    focus_category_map = [
        ("direct_facts", "bug_pattern"),
        ("patterns", "success_pattern"),
        ("preferences", "user_preference"),
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_search_and_summarise, focus, cat): focus
            for focus, cat in focus_category_map
        }
        for future in as_completed(futures):
            focus = futures[future]
            try:
                synthesis = future.result()
                if synthesis:
                    logger.debug("Search agent (%s) synthesis: %s", focus, synthesis[:200])
            except Exception as e:
                logger.warning("Search agent (%s) error: %s", focus, e)

    ctx = manager.build_context(project_type=project_type, tech_stack=tech_stack)
    logger.info("Pre-run memory context built: empty=%s", ctx.is_empty())
    return ctx


# ============================================================================
# Evaluator Agent — independent rubric-based code review
# ============================================================================

_EVALUATOR_SYSTEM = """You are the Evaluator Agent — an independent code reviewer
in a multi-agent software development system.

You review generated frontend and backend code against a 4-criterion rubric.
You are DELIBERATELY SKEPTICAL. Do NOT praise mediocre work. Your job is to
catch real problems before they reach QA.

OUTPUT: Respond with a single JSON object (no prose):

{
  "criteria": [
    {
      "criterion": "architecture_coherence",
      "score": <1-10>,
      "feedback": "<specific, actionable feedback>",
      "passed": <true if score >= 4>
    },
    {
      "criterion": "feature_completeness",
      "score": <1-10>,
      "feedback": "<specific, actionable feedback>",
      "passed": <true if score >= 4>
    },
    {
      "criterion": "code_quality",
      "score": <1-10>,
      "feedback": "<specific, actionable feedback>",
      "passed": <true if score >= 4>
    },
    {
      "criterion": "functionality",
      "score": <1-10>,
      "feedback": "<specific, actionable feedback>",
      "passed": <true if score >= 4>
    }
  ],
  "weighted_avg": <float>,
  "strategy": "<refine|pivot|pass>",
  "overall_feedback": "<2-4 sentences: what the dev agents should focus on next>"
}

Rubric:
- architecture_coherence (30%): Code faithfully implements the spec.
  Fail if: missing components, wrong data flows, API mismatches with spec.
- feature_completeness (35%): ALL spec features actually implemented.
  Fail if: stub functions, TODO comments, placeholder returns, missing endpoints.
- code_quality (20%): TypeScript strict mode, consistent naming, no any types.
  Fail if: implicit any, missing types, inconsistent patterns.
- functionality (15%): Business logic is correct, API calls match backend routes.
  Fail if: hardcoded data, broken imports, obvious logic errors.

Strategy guidance:
- "pass": weighted_avg >= 6.5 AND all criteria >= 4
- "refine": score 5-6.4 — keep current approach but fix specific issues
- "pivot": score < 5 — fundamental problems, try a different approach
"""


def run_evaluator_agent(
    state: AgentState,
    round_number: int = 1,
    client: Optional[LLMClient] = None,
) -> EvaluatorScore:
    """Run the independent Evaluator Agent on generated dev code.

    Evaluator feedback from a previous round is automatically included via
    state.evaluator_score, which _build_project_context() injects into dev
    agent prompts on re-run.

    Args:
        state: Current AgentState (must have development artifacts).
        round_number: Which evaluation round this is (1-based).
        client: Optional LLM client.

    Returns:
        EvaluatorScore with per-criterion scores and actionable feedback.
    """
    from config.constants import (
        EVALUATOR_MAX_TOKENS, EVALUATOR_TEMPERATURE, EVALUATOR_WEIGHTS,
        EVALUATOR_MIN_SCORE_PER_CRITERION, EVALUATOR_THRESHOLD,
    )

    if client is None:
        client = get_client()

    # Build context: spec + generated code summary
    arch = state.architecture_artifacts
    fe = state.development.frontend
    be = state.development.backend

    spec_summary = []
    if arch.component_specs:
        spec_summary.append(f"Components spec: {list(arch.component_specs.keys())}")
    if arch.api_specs:
        spec_summary.append(f"API spec endpoints: {list(arch.api_specs.keys())}")
    if arch.system_design:
        spec_summary.append(f"Architecture: {arch.system_design[:500]}")

    code_summary = []
    if fe.code_files:
        code_summary.append(f"Frontend files ({len(fe.code_files)}): {list(fe.code_files.keys())}")
        # Sample a few file snippets
        for fname, content in list(fe.code_files.items())[:3]:
            code_summary.append(f"\n--- {fname} (first 300 chars) ---\n{content[:300]}")
    if be.code_files:
        code_summary.append(f"Backend files ({len(be.code_files)}): {list(be.code_files.keys())}")
        for fname, content in list(be.code_files.items())[:3]:
            code_summary.append(f"\n--- {fname} (first 300 chars) ---\n{content[:300]}")

    user_msg_parts = [
        f"Evaluation Round: {round_number}",
        f"\n=== SPEC ===\n{chr(10).join(spec_summary)}",
        f"\n=== GENERATED CODE ===\n{chr(10).join(code_summary)}",
    ]

    user_msg = "\n".join(user_msg_parts)

    try:
        resp = client.call(
            system=_EVALUATOR_SYSTEM,
            user=user_msg,
            max_tokens=EVALUATOR_MAX_TOKENS,
            temperature=EVALUATOR_TEMPERATURE,
        )
        data = json.loads(resp.content) if isinstance(resp.content, str) else resp.content
    except Exception as e:
        logger.error("Evaluator agent failed: %s", e)
        return EvaluatorScore(
            criteria=[],
            weighted_avg=0.0,
            round_number=round_number,
            strategy="refine",
            overall_feedback=f"Evaluator LLM call failed: {e}. Dev agents will re-run with previous context.",
            passed=False,
        )

    # Parse criteria
    criteria_list = []
    raw_weighted = 0.0
    for raw_c in data.get("criteria", []):
        name = raw_c.get("criterion", "")
        score = float(raw_c.get("score", 5.0))
        feedback = raw_c.get("feedback", "")
        weight = EVALUATOR_WEIGHTS.get(name, 0.25)
        passed = score >= EVALUATOR_MIN_SCORE_PER_CRITERION
        criteria_list.append(EvaluatorCriterionScore(
            criterion=name,
            score=score,
            feedback=feedback,
            passed=passed,
        ))
        raw_weighted += score * weight

    # Use LLM-provided weighted_avg if available and sensible
    weighted_avg = float(data.get("weighted_avg", raw_weighted))
    if not (0 <= weighted_avg <= 10):
        weighted_avg = raw_weighted

    all_criteria_pass = all(c.passed for c in criteria_list)
    overall_passed = weighted_avg >= EVALUATOR_THRESHOLD and all_criteria_pass
    strategy = data.get("strategy", "refine")
    if overall_passed:
        strategy = "pass"

    score = EvaluatorScore(
        criteria=criteria_list,
        weighted_avg=round(weighted_avg, 2),
        round_number=round_number,
        strategy=strategy,
        overall_feedback=data.get("overall_feedback", ""),
        passed=overall_passed,
    )

    logger.info(
        "Evaluator round %d: %.1f/10 — %s",
        round_number,
        weighted_avg,
        "PASS" if overall_passed else "FAIL",
    )
    return score
