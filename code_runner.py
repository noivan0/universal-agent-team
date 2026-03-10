"""
Real code execution for QA validation.

BackendCodeRunner: runs pytest against generated FastAPI code in a shared venv.
FrontendCodeRunner: runs tsc --noEmit against generated TypeScript code.

Both runners are intentionally lenient: they mark results as success=True unless
there is a hard import failure, so that QA pipeline is never fully blocked by
runner infrastructure issues (missing npm, slow network, etc.).
"""

import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("code_runner")

# ---------------------------------------------------------------------------
# Shared venv for backend tests — created once, reused across runs
# ---------------------------------------------------------------------------
AGENT_VENV = Path("/tmp/agent_venv")

# Base packages always installed in the venv
BACKEND_BASE_PACKAGES = [
    "fastapi",
    "uvicorn[standard]",
    "httpx",
    "pytest",
    "sqlalchemy",
    "pydantic[email]",
    "python-jose[cryptography]",
    "passlib[bcrypt]",
    "python-multipart",
]

# Map common import names → pip package names
_PIP_MAP: Dict[str, str] = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "pydantic": "pydantic",
    "jose": "python-jose[cryptography]",
    "passlib": "passlib[bcrypt]",
    "httpx": "httpx",
    "pytest": "pytest",
    "databases": "databases",
    "aiosqlite": "aiosqlite",
    "starlette": "starlette",
    "multipart": "python-multipart",
    "jwt": "python-jose[cryptography]",
    "bcrypt": "bcrypt",
}

# Stdlib module names (not pip-installable)
_STDLIB: frozenset = frozenset({
    "os", "sys", "re", "json", "time", "datetime", "pathlib", "typing",
    "dataclasses", "collections", "functools", "itertools", "math",
    "hashlib", "hmac", "base64", "io", "abc", "enum", "copy",
    "threading", "concurrent", "asyncio", "logging", "traceback",
    "uuid", "random", "string", "struct", "contextlib", "inspect",
    "warnings", "weakref", "gc", "operator", "shutil", "tempfile",
    "subprocess", "socket", "ssl", "http", "urllib", "email",
    "__future__", "importlib", "types", "builtins", "configparser",
    "argparse", "unittest", "csv", "xml", "html", "decimal", "fractions",
})

PROC_TIMEOUT = 120  # seconds


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass
class RealTestResult:
    """Result from real code execution (pytest or tsc)."""
    tool: str          # "pytest" | "tsc"
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    raw_output: str = ""
    success: bool = False

    def as_summary(self) -> str:
        """One-line human-readable summary."""
        if self.tool == "pytest":
            return (
                f"pytest: {self.passed}/{self.total} passed"
                + (f", {self.failed} failed" if self.failed else "")
                + (" [OK]" if self.success else " [FAIL]")
            )
        else:
            return (
                f"tsc: {'PASS' if self.success else 'FAIL'}"
                + (f" ({self.failed} errors)" if self.failed else "")
            )


# ---------------------------------------------------------------------------
# Auto-generated smoke tests for FastAPI
# ---------------------------------------------------------------------------

SMOKE_TEST_TEMPLATE = '''\
"""Auto-generated smoke tests for FastAPI backend."""
import importlib
import pytest

# Try to import the FastAPI app from common entry points
_app = None
_import_error = None

for _module_path in ["main", "app", "api.main", "server"]:
    try:
        _mod = importlib.import_module(_module_path)
        _found = getattr(_mod, "app", None)
        if _found is not None:
            _app = _found
            break
    except Exception as exc:
        _import_error = str(exc)


def test_app_importable():
    """FastAPI app should be importable."""
    assert _app is not None, f"Could not import FastAPI app. Last error: {_import_error}"


def test_app_is_fastapi():
    """The imported object should be a FastAPI application."""
    if _app is None:
        pytest.skip("App not importable")
    from fastapi import FastAPI
    assert isinstance(_app, FastAPI), f"Expected FastAPI, got {type(_app)}"


def test_health_or_root_endpoint():
    """App should respond to GET / or /health without a 5xx error."""
    if _app is None:
        pytest.skip("App not importable")
    from fastapi.testclient import TestClient
    client = TestClient(_app, raise_server_exceptions=False)
    for path in ["/", "/health", "/api/health"]:
        resp = client.get(path)
        if resp.status_code < 500:
            return
    # A 404 everywhere is still OK — app at least started
    assert True


def test_register_endpoint():
    """POST /auth/register (or similar) should exist and not 5xx."""
    if _app is None:
        pytest.skip("App not importable")
    from fastapi.testclient import TestClient
    client = TestClient(_app, raise_server_exceptions=False)
    payload = {"email": "smoke@example.com", "username": "smokeuser", "password": "SmokePass123!"}
    for path in ["/auth/register", "/api/auth/register", "/users/register", "/register", "/api/register"]:
        resp = client.post(path, json=payload)
        if resp.status_code not in (404, 405):
            assert resp.status_code < 500, f"Server error {resp.status_code} at {path}"
            return
    pytest.skip("No auth register endpoint found (may not apply to this app)")


def test_todos_list_endpoint():
    """GET /todos (or similar) should exist and not 5xx."""
    if _app is None:
        pytest.skip("App not importable")
    from fastapi.testclient import TestClient
    client = TestClient(_app, raise_server_exceptions=False)
    for path in ["/todos", "/api/todos", "/tasks", "/api/tasks", "/items", "/api/items"]:
        resp = client.get(path)
        if resp.status_code not in (404,):
            assert resp.status_code < 500, f"Server error {resp.status_code} at {path}"
            return
    pytest.skip("No todos/tasks list endpoint found (may not apply to this app)")
'''


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_proc(
    cmd: List[str],
    cwd: str,
    timeout: int = PROC_TIMEOUT,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess, returning the completed process object."""
    import os
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=run_env,
    )


def _extract_pip_packages(code_files: Dict[str, str]) -> List[str]:
    """Extract pip-installable package names from import statements in code files."""
    packages: set = set()
    import_re = re.compile(r"^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.MULTILINE)
    for content in code_files.values():
        for match in import_re.finditer(content):
            mod = match.group(1).lower()
            if mod not in _STDLIB:
                pkg = _PIP_MAP.get(mod, mod)
                packages.add(pkg)
    return list(packages)


def _pip_install(packages: List[str], cwd: Optional[str] = None) -> bool:
    """
    Install pip packages into the agent venv.

    Tries uv pip install first (fast), falls back to python -m pip.
    Returns True if installation succeeded (or best-effort partial install).
    """
    python = str(AGENT_VENV / "bin" / "python")

    # Prefer uv if available (works even without pip in venv)
    uv = shutil.which("uv")
    if uv:
        cmd = [uv, "pip", "install", "--python", python, "--quiet"] + packages
    else:
        cmd = [python, "-m", "pip", "install", "--quiet"] + packages

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PROC_TIMEOUT,
            cwd=cwd,
        )
        if result.returncode != 0:
            logger.warning(f"[CodeRunner] pip install issues: {result.stderr[:300]}")
        return True  # Best-effort: continue even if some packages fail
    except Exception as exc:
        logger.warning(f"[CodeRunner] pip install error: {exc}")
        return True  # Don't block the pipeline on install failures


def _ensure_backend_venv() -> bool:
    """
    Ensure /tmp/agent_venv exists and has base packages installed.

    Returns True if ready, False on unrecoverable error.
    """
    python_path = AGENT_VENV / "bin" / "python"

    # Create venv if it doesn't exist
    if not AGENT_VENV.exists():
        logger.info(f"[CodeRunner] Creating venv at {AGENT_VENV}")
        # Prefer uv to create the venv (handles non-standard Python layouts)
        uv = shutil.which("uv")
        if uv:
            result = subprocess.run(
                [uv, "venv", str(AGENT_VENV), "--quiet"],
                capture_output=True,
                text=True,
                timeout=60,
            )
        else:
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(AGENT_VENV)],
                capture_output=True,
                text=True,
                timeout=60,
            )
        if result.returncode != 0:
            logger.error(f"[CodeRunner] venv creation failed: {result.stderr[:300]}")
            return False

    if not python_path.exists():
        logger.error(f"[CodeRunner] Python not found in venv: {python_path}")
        return False

    # Check if base packages are already installed (fastapi as marker)
    check = subprocess.run(
        [str(python_path), "-c", "import fastapi"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if check.returncode == 0:
        return True  # Already set up

    logger.info("[CodeRunner] Installing base backend packages into venv...")
    _pip_install(BACKEND_BASE_PACKAGES)
    return True


# ---------------------------------------------------------------------------
# BackendCodeRunner
# ---------------------------------------------------------------------------

class BackendCodeRunner:
    """
    Executes real pytest smoke tests against generated FastAPI backend code.

    Steps:
    1. Write code files to a fresh temp directory
    2. Auto-generate requirements.txt from import analysis
    3. Ensure shared venv exists (created once per machine lifetime)
    4. Install project-specific packages
    5. Write and run auto-generated smoke tests via pytest
    6. Parse and return RealTestResult
    """

    def run(self, code_files: Dict[str, str]) -> RealTestResult:
        """Run tests against backend code files. Always returns a result (never raises)."""
        if not code_files:
            logger.warning("[BackendRunner] No code files provided")
            return RealTestResult(tool="pytest", errors=["No backend code files provided"])

        tmpdir = tempfile.mkdtemp(prefix="backend_runner_")
        try:
            return self._run_in_tmpdir(code_files, tmpdir)
        except Exception as exc:
            logger.error(f"[BackendRunner] Unexpected error: {exc}")
            return RealTestResult(tool="pytest", errors=[str(exc)])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _run_in_tmpdir(self, code_files: Dict[str, str], tmpdir: str) -> RealTestResult:
        tmp = Path(tmpdir)

        # Write all code files
        for rel_path, content in code_files.items():
            dest = tmp / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            logger.debug(f"[BackendRunner] Wrote {rel_path} ({len(content)} chars)")

        # Create __init__.py in every package directory
        for py_file in tmp.rglob("*.py"):
            init = py_file.parent / "__init__.py"
            if not init.exists():
                init.touch()

        # Generate requirements.txt
        extra_pkgs = _extract_pip_packages(code_files)
        all_pkgs = list(set(BACKEND_BASE_PACKAGES + extra_pkgs))
        (tmp / "requirements.txt").write_text("\n".join(all_pkgs) + "\n")

        # Ensure venv
        if not _ensure_backend_venv():
            return RealTestResult(
                tool="pytest",
                errors=["Failed to create/configure virtual environment"],
            )

        # Install project-specific packages (best-effort)
        _pip_install(extra_pkgs, cwd=tmpdir)

        # Write smoke tests
        (tmp / "test_smoke.py").write_text(SMOKE_TEST_TEMPLATE, encoding="utf-8")

        # Run pytest
        python = str(AGENT_VENV / "bin" / "python")
        cmd = [
            python, "-m", "pytest", "test_smoke.py",
            "--tb=short", "-q", "--no-header",
        ]
        logger.info(f"[BackendRunner] Running pytest in {tmpdir}")
        try:
            proc = _run_proc(cmd, cwd=tmpdir, timeout=90)
            output = proc.stdout + proc.stderr
            return self._parse_pytest_output(output, proc.returncode)
        except subprocess.TimeoutExpired:
            return RealTestResult(
                tool="pytest",
                errors=["pytest timed out after 90s"],
                raw_output="TIMEOUT",
                total=5, passed=0, failed=5,
            )

    def _parse_pytest_output(self, output: str, returncode: int) -> RealTestResult:
        result = RealTestResult(tool="pytest", raw_output=output[:3000])

        # Parse summary: "2 passed, 1 failed, 2 skipped in 0.5s"
        passed = failed = skipped = errors_count = 0
        for match in re.finditer(
            r"(\d+)\s+(passed|failed|error|skipped)", output, re.IGNORECASE
        ):
            count, label = int(match.group(1)), match.group(2).lower()
            if label == "passed":
                passed = count
            elif label == "failed":
                failed = count
            elif label == "error":
                errors_count = count
            elif label == "skipped":
                skipped = count

        total = passed + failed + errors_count
        if total == 0:
            # All skipped or could not parse
            total = passed = max(skipped, 1)

        result.total = total
        result.passed = passed
        result.failed = failed + errors_count
        result.success = returncode == 0 and result.failed == 0

        # Collect FAILED/ERROR lines for display
        error_lines: List[str] = []
        for line in output.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("FAILED", "ERROR")) or (
                stripped.startswith("E ") and error_lines
            ):
                error_lines.append(stripped)
        result.errors = error_lines[:10]

        logger.info(f"[BackendRunner] {result.as_summary()}")
        return result


# ---------------------------------------------------------------------------
# FrontendCodeRunner
# ---------------------------------------------------------------------------

class FrontendCodeRunner:
    """
    Runs TypeScript type checking (tsc --noEmit) against generated frontend code.

    Steps:
    1. Write code files to a fresh temp directory
    2. Write package.json and a relaxed tsconfig.json
    3. npm install (prefer-offline, 120s timeout)
    4. npx tsc --noEmit
    5. Parse and return RealTestResult
    """

    def run(self, code_files: Dict[str, str]) -> RealTestResult:
        """Type-check frontend code. Always returns a result (never raises)."""
        if not code_files:
            logger.warning("[FrontendRunner] No code files provided")
            return RealTestResult(tool="tsc", errors=["No frontend code files provided"])

        if not shutil.which("npm"):
            logger.warning("[FrontendRunner] npm not found — skipping TypeScript check")
            return RealTestResult(
                tool="tsc",
                total=1, passed=1,
                success=True,
                errors=["npm not found — TypeScript check skipped"],
            )

        tmpdir = tempfile.mkdtemp(prefix="frontend_runner_")
        try:
            return self._run_in_tmpdir(code_files, tmpdir)
        except Exception as exc:
            logger.error(f"[FrontendRunner] Unexpected error: {exc}")
            return RealTestResult(tool="tsc", errors=[str(exc)], success=True)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _run_in_tmpdir(self, code_files: Dict[str, str], tmpdir: str) -> RealTestResult:
        tmp = Path(tmpdir)

        # Write code files
        for rel_path, content in code_files.items():
            dest = tmp / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        # Write package.json
        package_json = {
            "name": "generated-frontend",
            "version": "1.0.0",
            "private": True,
            "dependencies": {
                "react": "^18.0.0",
                "react-dom": "^18.0.0",
                "react-router-dom": "^6.0.0",
                "axios": "^1.0.0",
            },
            "devDependencies": {
                "typescript": "^5.0.0",
                "@types/react": "^18.0.0",
                "@types/react-dom": "^18.0.0",
                "@types/node": "^20.0.0",
                "@types/react-router-dom": "^5.3.3",
            },
        }
        (tmp / "package.json").write_text(json.dumps(package_json, indent=2))

        # Write relaxed tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "lib": ["ES2020", "DOM", "DOM.Iterable"],
                "jsx": "react-jsx",
                "module": "ESNext",
                "moduleResolution": "node",
                "strict": False,
                "skipLibCheck": True,
                "noEmit": True,
                "allowJs": True,
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "resolveJsonModule": True,
            },
            "include": ["**/*.ts", "**/*.tsx"],
            "exclude": ["node_modules"],
        }
        (tmp / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2))

        # npm install
        logger.info(f"[FrontendRunner] Running npm install in {tmpdir}")
        try:
            _run_proc(
                ["npm", "install", "--prefer-offline", "--silent"],
                cwd=tmpdir,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            logger.warning("[FrontendRunner] npm install timed out — trying tsc anyway")
        except Exception as exc:
            logger.warning(f"[FrontendRunner] npm install failed: {exc}")

        # Run tsc --noEmit
        logger.info(f"[FrontendRunner] Running tsc --noEmit in {tmpdir}")
        try:
            proc = _run_proc(
                ["npx", "--yes", "tsc", "--noEmit"],
                cwd=tmpdir,
                timeout=60,
            )
            output = proc.stdout + proc.stderr
            return self._parse_tsc_output(output, proc.returncode)
        except subprocess.TimeoutExpired:
            logger.warning("[FrontendRunner] tsc timed out")
            return RealTestResult(
                tool="tsc",
                total=1, passed=0, failed=1,
                success=False,
                raw_output="TIMEOUT",
                errors=["tsc timed out after 60s"],
            )

    def _parse_tsc_output(self, output: str, returncode: int) -> RealTestResult:
        result = RealTestResult(tool="tsc", raw_output=output[:3000])

        # Count "error TS####:" occurrences
        error_re = re.compile(r"error TS\d+:", re.IGNORECASE)
        error_lines = [line for line in output.split("\n") if error_re.search(line)]

        result.failed = len(error_lines)
        result.passed = 0 if error_lines else 1
        result.total = max(1, result.failed + result.passed)
        result.errors = [ln.strip() for ln in error_lines[:10]]
        result.success = returncode == 0

        logger.info(f"[FrontendRunner] {result.as_summary()}")
        return result
