"""
Unit tests for code_runner.py.

Tests cover:
- RealTestResult helper
- _extract_pip_packages
- BackendCodeRunner._parse_pytest_output
- FrontendCodeRunner._parse_tsc_output
- Timeout handling (tsc timeout must return success=False)
- Empty-file edge cases
- npm-not-found fallback
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from code_runner import (
    BackendCodeRunner,
    FrontendCodeRunner,
    RealTestResult,
    _extract_pip_packages,
)


# ============================================================================
# RealTestResult
# ============================================================================

class TestRealTestResult:
    def test_pytest_summary_all_pass(self):
        r = RealTestResult(tool="pytest", total=5, passed=5, failed=0, success=True)
        summary = r.as_summary()
        assert "pytest" in summary
        assert "5/5" in summary
        assert "[OK]" in summary

    def test_pytest_summary_some_fail(self):
        r = RealTestResult(tool="pytest", total=5, passed=3, failed=2, success=False)
        summary = r.as_summary()
        assert "3/5" in summary
        assert "2 failed" in summary
        assert "[FAIL]" in summary

    def test_tsc_summary_pass(self):
        r = RealTestResult(tool="tsc", total=1, passed=1, success=True)
        summary = r.as_summary()
        assert "tsc" in summary
        assert "PASS" in summary

    def test_tsc_summary_fail(self):
        r = RealTestResult(tool="tsc", total=3, failed=3, success=False)
        summary = r.as_summary()
        assert "FAIL" in summary
        assert "3 errors" in summary

    def test_default_success_is_false(self):
        r = RealTestResult(tool="pytest")
        assert r.success is False


# ============================================================================
# _extract_pip_packages
# ============================================================================

class TestExtractPipPackages:
    def test_fastapi_import(self):
        files = {"main.py": "from fastapi import FastAPI\nimport uvicorn\n"}
        pkgs = _extract_pip_packages(files)
        assert "fastapi" in pkgs
        assert "uvicorn" in pkgs

    def test_stdlib_excluded(self):
        files = {"utils.py": "import os\nimport json\nimport sys\n"}
        pkgs = _extract_pip_packages(files)
        assert "os" not in pkgs
        assert "json" not in pkgs
        assert "sys" not in pkgs

    def test_empty_files(self):
        pkgs = _extract_pip_packages({})
        assert pkgs == []

    def test_unknown_package_returned_as_is(self):
        files = {"app.py": "import some_custom_package\n"}
        pkgs = _extract_pip_packages(files)
        assert "some_custom_package" in pkgs

    def test_pip_map_applied(self):
        files = {"auth.py": "from jose import jwt\n"}
        pkgs = _extract_pip_packages(files)
        # jose maps to python-jose[cryptography]
        assert "python-jose[cryptography]" in pkgs


# ============================================================================
# BackendCodeRunner._parse_pytest_output
# ============================================================================

class TestBackendCodeRunnerParsePytest:
    def setup_method(self):
        self.runner = BackendCodeRunner()

    def test_parse_all_passed(self):
        output = "3 passed in 0.5s"
        result = self.runner._parse_pytest_output(output, returncode=0)
        assert result.passed == 3
        assert result.failed == 0
        assert result.success is True

    def test_parse_with_failures(self):
        output = "2 passed, 1 failed in 0.8s"
        result = self.runner._parse_pytest_output(output, returncode=1)
        assert result.passed == 2
        assert result.failed == 1
        assert result.success is False

    def test_parse_with_errors(self):
        output = "1 passed, 2 error in 0.3s"
        result = self.runner._parse_pytest_output(output, returncode=1)
        assert result.failed == 2
        assert result.success is False

    def test_parse_all_skipped(self):
        output = "5 skipped in 0.1s"
        result = self.runner._parse_pytest_output(output, returncode=0)
        # All skipped — total treated as max(skipped, 1), passed = skipped
        assert result.total >= 1

    def test_parse_error_lines_collected(self):
        output = (
            "FAILED test_smoke.py::test_app_importable - AssertionError\n"
            "1 failed in 0.2s"
        )
        result = self.runner._parse_pytest_output(output, returncode=1)
        assert len(result.errors) > 0
        assert any("FAILED" in e for e in result.errors)

    def test_nonzero_returncode_means_failure(self):
        output = "3 passed in 0.5s"
        result = self.runner._parse_pytest_output(output, returncode=1)
        # returncode != 0 → success=False even if output says passed
        assert result.success is False

    def test_empty_output(self):
        result = self.runner._parse_pytest_output("", returncode=0)
        assert isinstance(result, RealTestResult)
        assert result.tool == "pytest"


# ============================================================================
# BackendCodeRunner.run — subprocess mocked
# ============================================================================

class TestBackendCodeRunnerRun:
    def test_empty_files_returns_no_code_result(self):
        runner = BackendCodeRunner()
        result = runner.run({})
        assert result.tool == "pytest"
        assert result.success is False
        assert any("No backend code files" in e for e in result.errors)

    @patch("code_runner._ensure_backend_venv", return_value=True)
    @patch("code_runner._pip_install", return_value=True)
    @patch("code_runner._run_proc")
    def test_run_success(self, mock_proc, mock_pip, mock_venv):
        mock_proc.return_value = MagicMock(
            stdout="3 passed in 0.5s",
            stderr="",
            returncode=0,
        )
        runner = BackendCodeRunner()
        code_files = {"main.py": "from fastapi import FastAPI\napp = FastAPI()"}
        result = runner.run(code_files)
        assert result.tool == "pytest"
        assert result.success is True
        assert result.passed == 3

    @patch("code_runner._ensure_backend_venv", return_value=True)
    @patch("code_runner._pip_install", return_value=True)
    @patch("code_runner._run_proc", side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=90))
    def test_run_timeout(self, mock_proc, mock_pip, mock_venv):
        runner = BackendCodeRunner()
        result = runner.run({"main.py": "from fastapi import FastAPI"})
        assert result.tool == "pytest"
        assert result.success is False
        assert any("timed out" in e for e in result.errors)

    @patch("code_runner._ensure_backend_venv", return_value=False)
    def test_run_venv_failure(self, mock_venv):
        runner = BackendCodeRunner()
        result = runner.run({"main.py": "# code"})
        assert result.success is False
        assert any("virtual environment" in e for e in result.errors)


# ============================================================================
# FrontendCodeRunner._parse_tsc_output
# ============================================================================

class TestFrontendCodeRunnerParseTsc:
    def setup_method(self):
        self.runner = FrontendCodeRunner()

    def test_parse_no_errors(self):
        result = self.runner._parse_tsc_output("", returncode=0)
        assert result.success is True
        assert result.failed == 0
        assert result.passed == 1

    def test_parse_with_ts_errors(self):
        output = (
            "src/App.tsx(5,3): error TS2345: Argument of type 'number' is not assignable.\n"
            "src/App.tsx(8,1): error TS2304: Cannot find name 'foo'.\n"
        )
        result = self.runner._parse_tsc_output(output, returncode=1)
        assert result.failed == 2
        assert result.success is False
        assert len(result.errors) == 2

    def test_parse_returncode_determines_success(self):
        # No TS errors in text but non-zero returncode
        result = self.runner._parse_tsc_output("some warning", returncode=1)
        assert result.success is False

    def test_errors_truncated_to_10(self):
        lines = "\n".join(
            f"src/App.tsx({i},1): error TS2345: err" for i in range(15)
        )
        result = self.runner._parse_tsc_output(lines, returncode=1)
        assert len(result.errors) <= 10


# ============================================================================
# FrontendCodeRunner.run — subprocess mocked
# ============================================================================

class TestFrontendCodeRunnerRun:
    def test_empty_files_returns_no_code_result(self):
        runner = FrontendCodeRunner()
        result = runner.run({})
        assert result.tool == "tsc"
        assert result.success is False
        assert any("No frontend code files" in e for e in result.errors)

    @patch("code_runner.shutil.which", return_value=None)
    def test_no_npm_returns_skipped_result(self, mock_which):
        runner = FrontendCodeRunner()
        result = runner.run({"src/App.tsx": "export default function App() { return null; }"})
        assert result.tool == "tsc"
        # When npm is not found, runner skips gracefully and returns success=True (infra skip)
        assert result.success is True
        assert any("npm not found" in e for e in result.errors)

    @patch("code_runner.shutil.which", return_value="/usr/bin/npm")
    @patch("code_runner._run_proc")
    def test_tsc_timeout_returns_failure(self, mock_proc, mock_which):
        """CRITICAL: tsc timeout must return success=False (bug fix verification)."""
        # First call is npm install (succeeds), second is tsc (times out)
        mock_proc.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),
            subprocess.TimeoutExpired(cmd="tsc", timeout=60),
        ]
        runner = FrontendCodeRunner()
        result = runner.run({"src/App.tsx": "export default function App() {}"})
        assert result.tool == "tsc"
        assert result.success is False, "tsc timeout must return success=False"
        assert any("timed out" in e for e in result.errors)

    @patch("code_runner.shutil.which", return_value="/usr/bin/npm")
    @patch("code_runner._run_proc")
    def test_tsc_pass(self, mock_proc, mock_which):
        mock_proc.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),  # npm install
            MagicMock(stdout="", stderr="", returncode=0),  # tsc
        ]
        runner = FrontendCodeRunner()
        result = runner.run({"src/App.tsx": "export default function App() {}"})
        assert result.tool == "tsc"
        assert result.success is True

    @patch("code_runner.shutil.which", return_value="/usr/bin/npm")
    @patch("code_runner._run_proc")
    def test_tsc_type_errors(self, mock_proc, mock_which):
        ts_error = "src/App.tsx(1,1): error TS2304: Cannot find name 'x'."
        mock_proc.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),  # npm install
            MagicMock(stdout=ts_error, stderr="", returncode=1),  # tsc
        ]
        runner = FrontendCodeRunner()
        result = runner.run({"src/App.tsx": "x"})
        assert result.success is False
        assert result.failed == 1
