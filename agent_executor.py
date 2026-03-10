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
from typing import Any, Dict, List, Optional

from state_models import (
    AgentState, AgentError, AgentMessage, AgentPhase, ErrorType, StateUpdate,
    PlanningArtifacts, ArchitectureArtifacts, DevelopmentArtifacts,
    DevelopmentSection, TestingArtifacts, DocumentationArtifacts,
)
from artifact_schemas import ComponentSpec, APIEndpoint
from llm_client import LLMClient, LLMResponse, get_client
from agent_bus import get_bus
from code_runner import BackendCodeRunner, FrontendCodeRunner

logger = logging.getLogger("agent_executor")


# ============================================================================
# Shared helpers
# ============================================================================

def _build_project_context(state: AgentState) -> str:
    """Compact project context string injected into every agent prompt."""
    lines = [
        f"Project ID: {state.metadata.project_id}",
        f"User Request: {state.metadata.user_request}",
        f"Phase: {state.metadata.current_phase.value}",
    ]
    if state.metadata.tech_stack:
        lines.append(f"Tech Stack: {state.metadata.tech_stack}")
    if state.planning_artifacts.requirements:
        # Truncate large requirements to save tokens
        reqs = state.planning_artifacts.requirements
        if len(reqs) > 2000:
            reqs = reqs[:2000] + "\n...[truncated]"
        lines.append(f"\n--- Requirements ---\n{reqs}")
    if state.planning_artifacts.complexity_score:
        lines.append(f"Complexity Score: {state.planning_artifacts.complexity_score}/100")
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

        frontend_bugs = [
            b for b in bug_reports
            if isinstance(b, dict) and b.get("component", "").lower() in
               ("frontend", "react", "ui", "component") or
               b.get("severity") == "critical"
        ]
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

        backend_bugs = [
            b for b in bug_reports
            if isinstance(b, dict) and b.get("severity") in ("critical", "high")
        ]
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
# Dispatcher
# ============================================================================

AGENT_RUNNERS = {
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
        agent_id: One of planning, architecture, frontend, backend, qa, documentation
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
