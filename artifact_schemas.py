"""
Artifact schemas and validators for Universal Agent Team.

Defines expected structure and validation rules for all artifacts
produced by each agent. Ensures type safety and contract compliance.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


# ============================================================================
# Planning Agent Output Schema
# ============================================================================

class TaskDefinition(BaseModel):
    """A single task from Planning Agent."""
    task_id: str
    title: str
    description: str
    estimated_complexity: int  # 1-10
    dependencies: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)


class PlanningAgentOutput(BaseModel):
    """
    Schema for Planning Agent output.

    Expected artifact structure when Planning Agent completes.
    """
    requirements: str = Field(
        ...,
        description="Detailed requirements document"
    )
    tasks: List[TaskDefinition] = Field(
        default_factory=list,
        description="Breakdown of work into actionable tasks"
    )
    dependencies: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Task dependency graph {task_id: [depends_on_task_ids]}"
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Identified risks and ambiguities"
    )
    tech_stack: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Detected tech stack {frontend, backend, detected_from}"
    )
    complexity_score: int = Field(
        50,
        ge=1,
        le=100,
        description="Overall project complexity (1-100)"
    )
    complexity_factors: List[str] = Field(
        default_factory=list,
        description="Factors contributing to complexity"
    )
    summary: str = Field(
        default="",
        description="Compact summary for downstream agents"
    )

    @validator("complexity_score")
    def validate_complexity(cls, v):
        if not (1 <= v <= 100):
            raise ValueError("complexity_score must be between 1 and 100")
        return v


# ============================================================================
# Architecture Agent Output Schema
# ============================================================================

class ComponentSpec(BaseModel):
    """Specification for a UI component."""
    name: str
    description: str
    props: Dict[str, Any] = Field(default_factory=dict)
    state: List[str] = Field(default_factory=list)
    api_calls: List[str] = Field(default_factory=list)


class APIEndpoint(BaseModel):
    """Specification for an API endpoint."""
    path: str
    method: str = Field(..., regex="^(GET|POST|PUT|DELETE|PATCH)$")
    description: str
    request_schema: Dict[str, Any] = Field(default_factory=dict)
    response_schema: Dict[str, Any] = Field(default_factory=dict)
    authentication_required: bool = False
    rate_limit: Optional[int] = None


class ArchitectureAgentOutput(BaseModel):
    """
    Schema for Architecture Agent output.

    Expected artifact structure when Architecture Agent completes.
    """
    system_design: str = Field(
        ...,
        description="High-level system architecture description"
    )
    architecture_pattern: str = Field(
        default="",
        description="Architecture pattern used (MVC, microservices, etc.)"
    )
    component_specs: Dict[str, ComponentSpec] = Field(
        default_factory=dict,
        description="Frontend component specifications by name"
    )
    api_specs: Dict[str, APIEndpoint] = Field(
        default_factory=dict,
        description="Backend API specifications by path"
    )
    database_schema: str = Field(
        default="",
        description="Data model and database schema"
    )
    design_system: Optional[str] = Field(
        default=None,
        description="Design system / UI guidelines"
    )
    deployment_templates: Dict[str, str] = Field(
        default_factory=dict,
        description="Docker, Kubernetes, etc. templates {file_path: content}"
    )
    technology_decisions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Technology selections {frontend_specialization, backend_specialization}"
    )
    critical_sections: Dict[str, str] = Field(
        default_factory=dict,
        description="Which sections to include in state {section_name: full|summary}"
    )
    summary: str = Field(
        default="",
        description="Compact summary for downstream agents"
    )

    @validator("api_specs")
    def validate_api_specs(cls, v):
        for path, endpoint in v.items():
            if not path.startswith("/"):
                raise ValueError(f"API path must start with /: {path}")
        return v


# ============================================================================
# Development Agent Output Schema
# ============================================================================

class CodeFile(BaseModel):
    """A generated code file."""
    path: str
    language: str  # python, typescript, javascript, etc.
    content: str
    description: Optional[str] = None


class DevelopmentAgentOutput(BaseModel):
    """
    Schema for Frontend/Backend Agent output.

    Expected artifact structure when development agents complete.
    """
    code_files: Dict[str, str] = Field(
        ...,
        description="Generated code files {file_path: content}"
    )
    language: str = Field(
        ...,
        description="Primary language (typescript, python, etc.)"
    )
    framework: str = Field(
        ...,
        description="Primary framework (react, fastapi, etc.)"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="External package dependencies"
    )
    types: Dict[str, str] = Field(
        default_factory=dict,
        description="Type definitions {name: definition}"
    )
    tests: Dict[str, str] = Field(
        default_factory=dict,
        description="Test files {test_path: test_code}"
    )
    summary: str = Field(
        default="",
        description="Summary of generated components/endpoints"
    )
    depends_on: Dict[str, int] = Field(
        default_factory=dict,
        description="Dependency versions {agent_id: required_version}"
    )

    @validator("code_files")
    def validate_code_files(cls, v):
        if not v:
            raise ValueError("code_files cannot be empty")
        return v

    @validator("dependencies")
    def validate_dependencies(cls, v):
        # Remove duplicates
        return list(set(v))


# ============================================================================
# QA Agent Output Schema
# ============================================================================

class TestResult(BaseModel):
    """Result of a single test."""
    test_name: str
    status: str = Field(..., regex="^(passed|failed|skipped)$")
    duration_ms: float
    error_message: Optional[str] = None


class BugReport(BaseModel):
    """A bug found during testing."""
    bug_id: str
    severity: str = Field(..., regex="^(critical|high|medium|low)$")
    component: str
    description: str
    reproduction_steps: List[str] = Field(default_factory=list)
    suggested_fix: Optional[str] = None


class ErrorAnalysis(BaseModel):
    """Analysis of a test/validation failure."""
    root_cause: str  # "frontend_code", "backend_code", "api_contract", "architecture", etc.
    affected_agents: List[str] = Field(default_factory=list)
    severity: str = Field(..., regex="^(critical|high|medium|low)$")
    details: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str


class RestartPlan(BaseModel):
    """Plan for intelligent restart after failure."""
    error_analysis: ErrorAnalysis
    agents_to_restart: List[str] = Field(
        default_factory=list,
        description="Which agents should be re-executed"
    )
    execution_order: List[str] = Field(
        default_factory=list,
        description="Order to re-execute agents (respecting dependencies)"
    )
    reason: str
    expected_outcome: str


class QAAgentOutput(BaseModel):
    """
    Schema for QA Agent output.

    Expected artifact structure when QA Agent completes.
    """
    test_results: Dict[str, List[TestResult]] = Field(
        default_factory=dict,
        description="Test results by test suite {suite_name: [test_results]}"
    )
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    coverage_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    coverage_report: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed coverage report"
    )
    bug_reports: List[BugReport] = Field(
        default_factory=list,
        description="Bugs found during testing"
    )
    error_analysis: Optional[ErrorAnalysis] = None
    restart_plan: Optional[RestartPlan] = None
    summary: str = Field(
        default="",
        description="Summary of test results"
    )

    @validator("coverage_percent")
    def validate_coverage(cls, v):
        if not (0.0 <= v <= 100.0):
            raise ValueError("coverage_percent must be between 0 and 100")
        return v

    @validator("passed_tests", "failed_tests", always=True)
    def validate_test_counts(cls, v):
        if v < 0:
            raise ValueError("Test counts cannot be negative")
        return v


# ============================================================================
# Documentation Agent Output Schema
# ============================================================================

class DocumentationSection(BaseModel):
    """A section of documentation."""
    title: str
    content: str
    subsections: Optional[Dict[str, str]] = None


class DocumentationAgentOutput(BaseModel):
    """
    Schema for Documentation Agent output.

    Expected artifact structure when Documentation Agent completes.
    """
    readme: str = Field(
        ...,
        description="Project README with overview and setup"
    )
    api_docs: str = Field(
        default="",
        description="API documentation"
    )
    architecture_docs: str = Field(
        default="",
        description="System architecture documentation"
    )
    deployment_guide: str = Field(
        default="",
        description="Deployment and operations guide"
    )
    user_guide: str = Field(
        default="",
        description="End-user guide"
    )
    troubleshooting: str = Field(
        default="",
        description="Troubleshooting and FAQ"
    )
    summary: str = Field(
        default="",
        description="Summary of documentation"
    )


# ============================================================================
# Contract Validator Output Schema (Optional Agent)
# ============================================================================

class APIAlignment(BaseModel):
    """Alignment between frontend and backend API."""
    endpoint: str
    frontend_usage: Optional[Dict[str, Any]] = None
    backend_spec: Optional[Dict[str, Any]] = None
    is_aligned: bool
    issues: List[str] = Field(default_factory=list)


class ContractValidatorOutput(BaseModel):
    """
    Schema for Contract Validator Agent output.

    Optional agent that validates API contracts between frontend and backend.
    """
    api_alignments: List[APIAlignment] = Field(
        default_factory=list,
        description="Alignment results for each API endpoint"
    )
    total_endpoints: int = 0
    aligned_endpoints: int = 0
    misaligned_endpoints: int = 0
    mismatches: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed mismatch information"
    )
    is_valid: bool = True
    summary: str = Field(
        default="",
        description="Summary of validation results"
    )


# ============================================================================
# Schema Validators
# ============================================================================

class SchemaValidator:
    """Validates artifact schemas."""

    @staticmethod
    def validate_planning_output(output: Dict[str, Any]) -> bool:
        """Validate Planning Agent output."""
        try:
            PlanningAgentOutput(**output)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_architecture_output(output: Dict[str, Any]) -> bool:
        """Validate Architecture Agent output."""
        try:
            ArchitectureAgentOutput(**output)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_development_output(output: Dict[str, Any]) -> bool:
        """Validate Frontend/Backend Agent output."""
        try:
            DevelopmentAgentOutput(**output)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_qa_output(output: Dict[str, Any]) -> bool:
        """Validate QA Agent output."""
        try:
            QAAgentOutput(**output)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_documentation_output(output: Dict[str, Any]) -> bool:
        """Validate Documentation Agent output."""
        try:
            DocumentationAgentOutput(**output)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_contract_validator_output(output: Dict[str, Any]) -> bool:
        """Validate Contract Validator Agent output."""
        try:
            ContractValidatorOutput(**output)
            return True
        except Exception:
            return False
