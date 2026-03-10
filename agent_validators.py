"""
Agent output validators for Universal Agent Team.

Validates agent outputs before they are applied to the state,
catching errors at production time (in the producing agent) rather
than at consumption time (in the consuming agent).

Each validator runs a lightweight rubric check on the agent's output dict
and returns a ValidationResult that the orchestrator can act on:
  - passed=True  → apply output to state and continue
  - passed=False, blocking=True  → retry or escalate
  - passed=False, blocking=False → log warning and continue
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from state_models import AgentState


# ============================================================================
# Validation Models
# ============================================================================

class ValidationIssue(BaseModel):
    """A single validation issue found in agent output."""
    field: str
    message: str
    blocking: bool = True  # If True, the orchestrator should not apply the output


class ValidationResult(BaseModel):
    """Result of validating an agent's output."""
    agent_id: str
    passed: bool
    issues: List[ValidationIssue] = Field(default_factory=list)

    @property
    def blocking_issues(self) -> List[ValidationIssue]:
        """Issues that prevent applying the output to state."""
        return [i for i in self.issues if i.blocking]

    @property
    def has_blocking_issues(self) -> bool:
        """True if any issue would block applying the output."""
        return any(i.blocking for i in self.issues)


# ============================================================================
# Agent Output Validators
# ============================================================================

class AgentOutputValidator:
    """Routes output validation to the correct per-agent validator."""

    @staticmethod
    def validate(
        agent_id: str,
        output: Dict[str, Any],
        state: AgentState
    ) -> ValidationResult:
        """
        Validate an agent's output dict.

        Args:
            agent_id: Which agent produced the output
            output: The output dict to validate
            state: Current project state (for cross-agent context checks)

        Returns:
            ValidationResult with pass/fail and list of issues
        """
        validators = {
            "planning": AgentOutputValidator._validate_planning,
            "architecture": AgentOutputValidator._validate_architecture,
            "frontend": AgentOutputValidator._validate_development,
            "backend": AgentOutputValidator._validate_development,
            "qa": AgentOutputValidator._validate_qa,
            "documentation": AgentOutputValidator._validate_documentation,
        }
        fn = validators.get(agent_id, AgentOutputValidator._validate_generic)
        return fn(agent_id, output, state)

    # ------------------------------------------------------------------
    # Per-agent validators
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_planning(
        agent_id: str,
        output: Dict[str, Any],
        state: AgentState
    ) -> ValidationResult:
        """Planning Agent: must produce requirements and at least one task."""
        issues: List[ValidationIssue] = []

        if not output.get("requirements"):
            issues.append(ValidationIssue(
                field="requirements",
                message="requirements field is empty or missing",
                blocking=True
            ))

        tasks = output.get("tasks", [])
        if len(tasks) < 1:
            issues.append(ValidationIssue(
                field="tasks",
                message="Planning Agent must produce at least 1 task",
                blocking=True
            ))

        complexity_score = output.get("complexity_score", 50)
        if not isinstance(complexity_score, (int, float)) or not (1 <= complexity_score <= 100):
            issues.append(ValidationIssue(
                field="complexity_score",
                message=f"complexity_score must be 1-100, got {complexity_score!r}",
                blocking=False
            ))

        return ValidationResult(
            agent_id=agent_id,
            passed=not any(i.blocking for i in issues),
            issues=issues
        )

    @staticmethod
    def _validate_architecture(
        agent_id: str,
        output: Dict[str, Any],
        state: AgentState
    ) -> ValidationResult:
        """Architecture Agent: must produce system_design and specs matching the tech stack."""
        issues: List[ValidationIssue] = []

        if not output.get("system_design"):
            issues.append(ValidationIssue(
                field="system_design",
                message="system_design is empty or missing",
                blocking=True
            ))

        tech_stack = (state.planning_artifacts.tech_stack or {})
        if tech_stack.get("frontend") and not output.get("component_specs"):
            issues.append(ValidationIssue(
                field="component_specs",
                message=(
                    f"component_specs required when frontend tech is specified "
                    f"({tech_stack['frontend']})"
                ),
                blocking=True
            ))

        if tech_stack.get("backend") and not output.get("api_specs"):
            issues.append(ValidationIssue(
                field="api_specs",
                message=(
                    f"api_specs required when backend tech is specified "
                    f"({tech_stack['backend']})"
                ),
                blocking=True
            ))

        return ValidationResult(
            agent_id=agent_id,
            passed=not any(i.blocking for i in issues),
            issues=issues
        )

    @staticmethod
    def _validate_development(
        agent_id: str,
        output: Dict[str, Any],
        state: AgentState
    ) -> ValidationResult:
        """Frontend / Backend Agent: must produce at least one code file."""
        issues: List[ValidationIssue] = []

        code_files = output.get("code_files", {})
        if not code_files:
            issues.append(ValidationIssue(
                field="code_files",
                message=f"{agent_id} agent produced no code files",
                blocking=True
            ))

        return ValidationResult(
            agent_id=agent_id,
            passed=not any(i.blocking for i in issues),
            issues=issues
        )

    @staticmethod
    def _validate_qa(
        agent_id: str,
        output: Dict[str, Any],
        state: AgentState
    ) -> ValidationResult:
        """QA Agent: must provide test_results; warns when coverage < 80%."""
        issues: List[ValidationIssue] = []

        test_results = output.get("test_results")
        if not test_results:
            issues.append(ValidationIssue(
                field="test_results",
                message="test_results is missing from QA output",
                blocking=True
            ))
        else:
            total = test_results.get("total", 0)
            if total == 0:
                issues.append(ValidationIssue(
                    field="test_results.total",
                    message="No tests were run",
                    blocking=False
                ))

            coverage = test_results.get("coverage", 0)
            if coverage < 80:
                issues.append(ValidationIssue(
                    field="test_results.coverage",
                    message=f"Coverage {coverage}% is below the 80% threshold",
                    blocking=False
                ))

        return ValidationResult(
            agent_id=agent_id,
            passed=not any(i.blocking for i in issues),
            issues=issues
        )

    @staticmethod
    def _validate_documentation(
        agent_id: str,
        output: Dict[str, Any],
        state: AgentState
    ) -> ValidationResult:
        """Documentation Agent: must produce a README at minimum."""
        issues: List[ValidationIssue] = []

        if not output.get("readme"):
            issues.append(ValidationIssue(
                field="readme",
                message="Documentation Agent must produce a README",
                blocking=True
            ))

        return ValidationResult(
            agent_id=agent_id,
            passed=not any(i.blocking for i in issues),
            issues=issues
        )

    @staticmethod
    def _validate_generic(
        agent_id: str,
        output: Dict[str, Any],
        state: AgentState
    ) -> ValidationResult:
        """Fallback: any non-empty output dict is considered valid."""
        issues: List[ValidationIssue] = []

        if not output:
            issues.append(ValidationIssue(
                field="output",
                message=f"Agent '{agent_id}' produced no output",
                blocking=True
            ))

        return ValidationResult(
            agent_id=agent_id,
            passed=not any(i.blocking for i in issues),
            issues=issues
        )
