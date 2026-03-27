"""
Unit tests for agent_executor.py.

Tests cover:
- run_planning_agent: valid JSON → StateUpdate with PlanningArtifacts
- run_architecture_agent: valid JSON → ArchitectureArtifacts with typed specs
- run_frontend_agent: valid JSON → DevelopmentArtifacts + publishes to bus
- run_backend_agent: valid JSON → DevelopmentArtifacts + publishes to bus
- run_frontend_agent in healing mode: bug_reports in context
- run_backend_agent in healing mode
- execute_agent dispatcher: known agents dispatched, unknown → ValueError
- Error handling: invalid JSON from LLM → ValueError propagated
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from agent_executor import (
    AGENT_RUNNERS,
    execute_agent,
    run_architecture_agent,
    run_backend_agent,
    run_documentation_agent,
    run_frontend_agent,
    run_planning_agent,
)
from agent_bus import reset_bus, get_bus
from llm_client import LLMClient, LLMResponse
from state_models import (
    AgentPhase,
    AgentState,
    ArchitectureArtifacts,
    DevelopmentArtifacts,
    DevelopmentSection,
    PlanningArtifacts,
    StateUpdate,
    TestingArtifacts,
    create_initial_state,
)
from artifact_schemas import ComponentSpec, APIEndpoint


# ============================================================================
# Helpers
# ============================================================================

def _make_state(user_request: str = "Build a todo app") -> AgentState:
    state = create_initial_state(
        project_id="test_exec_001",
        user_request=user_request,
    )
    return state


def _make_state_with_arch() -> AgentState:
    """State with planning + architecture already done."""
    state = _make_state()
    state.planning_artifacts.requirements = "Build a todo app with CRUD operations."
    state.planning_artifacts.tasks = [
        {"task_id": "T001", "title": "Frontend", "description": "React UI"}
    ]
    state.planning_artifacts.complexity_score = 40

    state.architecture_artifacts.system_design = "SPA with REST API"
    state.architecture_artifacts.database_schema = "todos(id, title, done)"
    state.architecture_artifacts.component_specs = {
        "TodoList": ComponentSpec(name="TodoList", description="List component"),
    }
    state.architecture_artifacts.api_specs = {
        "todos-list": APIEndpoint(
            path="/api/todos", method="GET", description="List todos"
        ),
        "todos-create": APIEndpoint(
            path="/api/todos", method="POST", description="Create todo"
        ),
    }
    return state


def _make_client_with_response(json_dict: Dict[str, Any]) -> LLMClient:
    """Return a mock LLMClient that always returns the given dict as JSON."""
    import json
    client = MagicMock(spec=LLMClient)
    response = LLMResponse(
        content=json.dumps(json_dict),
        model_used="claude-opus-4-6",
        input_tokens=100,
        output_tokens=200,
    )
    client.call.return_value = response
    client.extract_json.return_value = json_dict
    return client


# ============================================================================
# run_planning_agent
# ============================================================================

class TestRunPlanningAgent:
    def test_valid_response_returns_state_update(self):
        planning_data = {
            "requirements": "Build a todo app with auth and CRUD.",
            "complexity_score": 45,
            "complexity_factors": ["auth", "crud"],
            "tasks": [
                {"task_id": "T001", "title": "Frontend", "description": "React UI",
                 "phase": "frontend", "estimated_complexity": 5},
                {"task_id": "T002", "title": "Backend", "description": "FastAPI",
                 "phase": "backend", "estimated_complexity": 5},
            ],
            "dependencies": {"T002": ["T001"]},
            "risks": ["Authentication complexity", "Database design"],
            "tech_stack": {"frontend": "React", "backend": "FastAPI"},
            "summary": "Simple todo app.",
        }
        state = _make_state()
        client = _make_client_with_response(planning_data)

        update = run_planning_agent(state, client=client)

        assert isinstance(update, StateUpdate)
        assert update.planning_artifacts is not None
        assert update.planning_artifacts.requirements == "Build a todo app with auth and CRUD."
        assert update.planning_artifacts.complexity_score == 45
        assert len(update.planning_artifacts.tasks) == 2
        assert len(update.planning_artifacts.risks) == 2
        assert update.current_phase == AgentPhase.ARCHITECTURE
        assert update.message is not None
        assert "planning_agent" in update.message.agent_id

    def test_missing_optional_fields_use_defaults(self):
        minimal_data = {
            "requirements": "Minimal req",
            "complexity_score": 30,
            "tasks": [],
            "risks": [],
        }
        state = _make_state()
        client = _make_client_with_response(minimal_data)

        update = run_planning_agent(state, client=client)

        assert update.planning_artifacts.complexity_factors == []
        assert update.planning_artifacts.dependencies == {}
        assert update.planning_artifacts.tech_stack is None

    def test_invalid_json_raises(self):
        client = MagicMock(spec=LLMClient)
        response = LLMResponse(
            content="Not JSON at all", model_used="claude-opus-4-6",
            input_tokens=10, output_tokens=5
        )
        client.call.return_value = response
        client.extract_json.side_effect = ValueError("not valid JSON")

        state = _make_state()
        with pytest.raises(ValueError):
            run_planning_agent(state, client=client)


# ============================================================================
# run_architecture_agent
# ============================================================================

class TestRunArchitectureAgent:
    def test_valid_response_creates_typed_specs(self):
        arch_data = {
            "system_design": "Monolithic SPA with REST API.",
            "component_specs": {
                "TodoList": {
                    "name": "TodoList",
                    "description": "Renders todos",
                    "props": {"todos": "array"},
                    "state": ["loading"],
                    "api_calls": ["/api/todos"],
                },
            },
            "api_specs": {
                "todos-list": {
                    "path": "/api/todos",
                    "method": "GET",
                    "description": "Return all todos",
                    "request_schema": {},
                    "response_schema": {"todos": "array"},
                    "authentication_required": False,
                },
            },
            "database_schema": "todos(id, title, done)",
            "technology_decisions": {
                "frontend_framework": "React",
                "backend_framework": "FastAPI",
                "database": "SQLite",
                "rationale": "Simple stack for a todo app",
            },
            "summary": "Clean SPA architecture.",
        }
        state = _make_state()
        state.planning_artifacts.requirements = "Build a todo app"
        client = _make_client_with_response(arch_data)

        update = run_architecture_agent(state, client=client)

        assert isinstance(update, StateUpdate)
        assert update.architecture_artifacts is not None
        assert "TodoList" in update.architecture_artifacts.component_specs
        spec = update.architecture_artifacts.component_specs["TodoList"]
        assert isinstance(spec, ComponentSpec)
        assert spec.description == "Renders todos"

        assert "todos-list" in update.architecture_artifacts.api_specs
        ep = update.architecture_artifacts.api_specs["todos-list"]
        assert isinstance(ep, APIEndpoint)
        assert ep.method == "GET"
        assert ep.path == "/api/todos"

        assert update.current_phase == AgentPhase.FRONTEND

    def test_invalid_method_defaults_to_get(self):
        arch_data = {
            "system_design": "Design",
            "component_specs": {},
            "api_specs": {
                "bad-method": {
                    "path": "/api/test",
                    "method": "INVALID",
                    "description": "test",
                    "request_schema": {},
                    "response_schema": {},
                    "authentication_required": False,
                }
            },
            "database_schema": "",
            "technology_decisions": {},
            "summary": "",
        }
        state = _make_state()
        client = _make_client_with_response(arch_data)

        update = run_architecture_agent(state, client=client)

        ep = update.architecture_artifacts.api_specs["bad-method"]
        assert ep.method == "GET"


# ============================================================================
# run_frontend_agent
# ============================================================================

class TestRunFrontendAgent:
    def setup_method(self):
        reset_bus()

    def test_valid_response_creates_artifacts(self):
        frontend_data = {
            "code_files": {
                "src/App.tsx": "export default function App() { return null; }",
                "src/components/TodoList.tsx": "export default function TodoList() { return null; }",
            },
            "dependencies": ["react", "axios"],
            "api_calls": [
                {"method": "GET", "url": "/api/todos"},
                {"method": "POST", "url": "/api/todos"},
            ],
            "summary": "React frontend with TodoList component.",
        }
        state = _make_state_with_arch()
        client = _make_client_with_response(frontend_data)

        update = run_frontend_agent(state, client=client)

        assert isinstance(update, StateUpdate)
        assert update.development is not None
        assert "src/App.tsx" in update.development.frontend.code_files
        assert len(update.development.frontend.code_files) == 2
        assert update.message is not None
        assert "frontend_agent" in update.message.agent_id

    def test_publishes_api_calls_to_bus(self):
        frontend_data = {
            "code_files": {"src/App.tsx": "// app"},
            "dependencies": [],
            "api_calls": [
                {"method": "GET", "url": "/api/todos"},
                {"method": "POST", "url": "/api/todos"},
            ],
            "summary": "Frontend",
        }
        state = _make_state_with_arch()
        client = _make_client_with_response(frontend_data)

        run_frontend_agent(state, client=client)

        payload = get_bus().get_latest_payload("frontend.api_calls")
        assert payload is not None
        assert len(payload) == 2
        assert payload[0]["url"] == "/api/todos"

    def test_healing_mode_includes_bug_context(self):
        """In healing mode, bug reports must be passed to LLM (check via call args)."""
        frontend_data = {
            "code_files": {"src/App.tsx": "// fixed app"},
            "dependencies": [],
            "api_calls": [],
            "summary": "Fixed frontend.",
        }
        state = _make_state_with_arch()
        state.development.frontend.code_files = {"src/App.tsx": "// broken"}
        client = _make_client_with_response(frontend_data)

        bug_reports = [
            {"bug_id": "BUG_001", "severity": "critical", "component": "frontend",
             "description": "Component crashes on load", "suggested_fix": "Add null check"}
        ]
        update = run_frontend_agent(state, client=client, bug_reports=bug_reports)

        # Should succeed and return the fixed code
        assert update.development.frontend.code_files["src/App.tsx"] == "// fixed app"
        # Verify the LLM was called (healing mode passes bug context in prompt)
        assert client.call.called
        call_kwargs = client.call.call_args
        user_content = call_kwargs[1]["messages"][0]["content"] if call_kwargs[1] else call_kwargs[0][1][0]["content"]
        # Bug info should appear in the context sent to LLM
        assert "BUG_001" in user_content or "crashes" in user_content

    def test_invalid_code_files_defaults_to_empty(self):
        frontend_data = {
            "code_files": "not a dict",  # Invalid
            "dependencies": [],
            "api_calls": [],
            "summary": "Bad output.",
        }
        state = _make_state_with_arch()
        client = _make_client_with_response(frontend_data)

        update = run_frontend_agent(state, client=client)
        assert update.development.frontend.code_files == {}


# ============================================================================
# run_backend_agent
# ============================================================================

class TestRunBackendAgent:
    def setup_method(self):
        reset_bus()

    def test_valid_response_creates_artifacts(self):
        backend_data = {
            "code_files": {
                "main.py": "from fastapi import FastAPI\napp = FastAPI()",
                "routers/todos.py": "# todos router",
            },
            "dependencies": ["fastapi", "sqlalchemy"],
            "api_routes": [
                {"method": "GET", "path": "/api/todos"},
                {"method": "POST", "path": "/api/todos"},
            ],
            "summary": "FastAPI backend with todos CRUD.",
        }
        state = _make_state_with_arch()
        client = _make_client_with_response(backend_data)

        update = run_backend_agent(state, client=client)

        assert isinstance(update, StateUpdate)
        assert update.development is not None
        assert "main.py" in update.development.backend.code_files
        assert update.current_phase == AgentPhase.QA

    def test_publishes_api_routes_to_bus(self):
        backend_data = {
            "code_files": {"main.py": "app = FastAPI()"},
            "dependencies": [],
            "api_routes": [
                {"method": "GET", "path": "/api/todos"},
                {"method": "DELETE", "path": "/api/todos/{id}"},
            ],
            "summary": "Backend.",
        }
        state = _make_state_with_arch()
        client = _make_client_with_response(backend_data)

        run_backend_agent(state, client=client)

        payload = get_bus().get_latest_payload("backend.api_routes")
        assert payload is not None
        assert len(payload) == 2

    def test_healing_mode_passes_bugs_in_context(self):
        backend_data = {
            "code_files": {"main.py": "from fastapi import FastAPI\napp = FastAPI()"},
            "dependencies": [],
            "api_routes": [{"method": "GET", "path": "/api/todos"}],
            "summary": "Fixed backend.",
        }
        state = _make_state_with_arch()
        state.development.backend.code_files = {"main.py": "# broken"}
        client = _make_client_with_response(backend_data)

        bug_reports = [
            {"bug_id": "BUG_002", "severity": "critical", "component": "backend",
             "description": "Missing auth middleware", "suggested_fix": "Add JWT middleware"}
        ]
        update = run_backend_agent(state, client=client, bug_reports=bug_reports)
        assert "main.py" in update.development.backend.code_files


# ============================================================================
# execute_agent dispatcher
# ============================================================================

class TestExecuteAgentDispatcher:
    def test_unknown_agent_raises_value_error(self):
        state = _make_state()
        with pytest.raises(ValueError, match="Unknown agent_id"):
            execute_agent("nonexistent_agent", state)

    def test_all_known_agents_in_dispatcher(self):
        expected = {
            # Main workflow agents
            "planning", "architecture", "frontend", "backend", "qa", "documentation",
            # Brainstorming phase agents
            "brainstorming_planning", "brainstorming_architecture", "brainstorming_frontend",
            "brainstorming_backend", "brainstorming_qa", "brainstorming_documentation",
            "brainstorming_synthesis",
        }
        assert set(AGENT_RUNNERS.keys()) == expected

    def test_dispatches_to_planning(self):
        # AGENT_RUNNERS holds original refs at import; patch via patch.dict
        import agent_executor as ae
        mock_planning = MagicMock(return_value=StateUpdate())
        state = _make_state()
        with patch.dict(ae.AGENT_RUNNERS, {"planning": mock_planning}):
            execute_agent("planning", state)
        mock_planning.assert_called_once_with(state, None)

    def test_dispatches_bug_reports_to_frontend(self):
        import agent_executor as ae
        mock_frontend = MagicMock(return_value=StateUpdate())
        state = _make_state()
        bugs = [{"bug_id": "B001", "severity": "critical"}]
        with patch.dict(ae.AGENT_RUNNERS, {"frontend": mock_frontend}):
            execute_agent("frontend", state, bug_reports=bugs)
        mock_frontend.assert_called_once_with(state, None, bugs)

    def test_dispatches_bug_reports_to_backend(self):
        import agent_executor as ae
        mock_backend = MagicMock(return_value=StateUpdate())
        state = _make_state()
        bugs = [{"bug_id": "B002", "severity": "high"}]
        with patch.dict(ae.AGENT_RUNNERS, {"backend": mock_backend}):
            execute_agent("backend", state, bug_reports=bugs)
        mock_backend.assert_called_once_with(state, None, bugs)

    def test_bug_reports_not_passed_to_non_dev_agents(self):
        import agent_executor as ae
        mock_planning = MagicMock(return_value=StateUpdate())
        state = _make_state()
        bugs = [{"bug_id": "B003", "severity": "high"}]
        with patch.dict(ae.AGENT_RUNNERS, {"planning": mock_planning}):
            execute_agent("planning", state, bug_reports=bugs)
        # planning agent should NOT receive bug_reports (not a dev agent)
        mock_planning.assert_called_once_with(state, None)


# ============================================================================
# run_documentation_agent
# ============================================================================

class TestRunDocumentationAgent:
    def test_valid_response_creates_documentation(self):
        doc_data = {
            "readme": "# Todo App\nA simple todo application.",
            "api_docs": "## GET /api/todos\nReturns all todos.",
            "architecture_docs": "Monolithic SPA.",
            "deployment_guide": "pip install && uvicorn main:app",
            "summary": "Complete documentation generated.",
        }
        state = _make_state_with_arch()
        state.development.frontend.code_files = {"src/App.tsx": "// app"}
        state.development.backend.code_files = {"main.py": "# api"}
        state.testing_artifacts.test_results = {"total": 5, "passed": 5, "coverage": 85.0}
        client = _make_client_with_response(doc_data)

        update = run_documentation_agent(state, client=client)

        assert isinstance(update, StateUpdate)
        assert update.documentation_artifacts is not None
        assert update.documentation_artifacts.readme.startswith("# Todo App")
        assert update.documentation_artifacts.summary == "Complete documentation generated."
        assert update.is_complete is True
        assert update.current_phase == AgentPhase.COMPLETE
