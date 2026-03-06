"""
Unit tests for artifact schema validation.

Tests cover:
- Output validation for each agent type
- Artifact structure and typing
- Optional/required field validation
- Schema consistency across versions
"""

import pytest
from state_models import (
    PlanningArtifacts,
    ArchitectureArtifacts,
    DevelopmentArtifacts,
    TestingArtifacts,
    DocumentationArtifacts,
    ArtifactMetadata,
    ArtifactManifest,
    TaskStatus,
    AgentMessage,
)


@pytest.mark.unit
class TestPlanningArtifactSchema:
    """Test Planning Agent artifact schema validation."""

    def test_minimal_planning_artifacts(self):
        """Test minimal valid planning artifacts."""
        artifacts = PlanningArtifacts()

        assert artifacts.requirements is None
        assert artifacts.tasks == []
        assert artifacts.dependencies == {}
        assert artifacts.risks == []
        assert artifacts.complexity_score == 50

    def test_complete_planning_artifacts(self):
        """Test complete planning artifacts."""
        artifacts = PlanningArtifacts(
            requirements="Build a complete application",
            tasks=[
                {"task_id": "T001", "title": "Design"},
                {"task_id": "T002", "title": "Implement"}
            ],
            dependencies={"T002": ["T001"]},
            risks=["Timeline risk"],
            summary="High-level summary",
            complexity_score=75,
            complexity_factors=["api", "database"]
        )

        assert artifacts.requirements is not None
        assert len(artifacts.tasks) == 2
        assert "T001" in artifacts.dependencies or "T002" in artifacts.dependencies

    def test_planning_tech_stack_schema(self):
        """Test technology stack in planning artifacts."""
        artifacts = PlanningArtifacts(
            tech_stack={
                "frontend": "React",
                "backend": "FastAPI",
                "database": "PostgreSQL",
                "cache": "Redis"
            }
        )

        assert len(artifacts.tech_stack) == 4
        assert artifacts.tech_stack["frontend"] == "React"

    def test_planning_artifacts_validation(self):
        """Test that invalid planning artifacts fail validation."""
        # All these should work (None is valid for optional fields)
        valid_artifacts = [
            PlanningArtifacts(),
            PlanningArtifacts(requirements="Valid"),
            PlanningArtifacts(complexity_score=100),
            PlanningArtifacts(tasks=[{"id": "1"}])
        ]

        for artifacts in valid_artifacts:
            assert isinstance(artifacts, PlanningArtifacts)


@pytest.mark.unit
class TestArchitectureArtifactSchema:
    """Test Architecture Agent artifact schema validation."""

    def test_minimal_architecture_artifacts(self):
        """Test minimal valid architecture artifacts."""
        artifacts = ArchitectureArtifacts()

        assert artifacts.system_design is None
        assert artifacts.component_specs == {}
        assert artifacts.api_specs == {}

    def test_component_specs_schema(self):
        """Test component specification schema."""
        artifacts = ArchitectureArtifacts()
        artifacts.component_specs = {
            "Header": {
                "type": "React.FC",
                "props": ["title", "onLogout"],
                "state": [],
                "children": ["nav"]
            },
            "MainContent": {
                "type": "React.FC",
                "props": ["data"],
                "state": ["loading"]
            }
        }

        assert len(artifacts.component_specs) == 2
        header = artifacts.component_specs["Header"]
        assert header["type"] == "React.FC"
        assert "title" in header["props"]

    def test_api_specs_schema(self):
        """Test API specification schema."""
        artifacts = ArchitectureArtifacts()
        artifacts.api_specs = {
            "/users": {
                "GET": {
                    "description": "Get all users",
                    "response_schema": {"users": "array"},
                    "status_codes": [200, 401]
                },
                "POST": {
                    "description": "Create user",
                    "request_schema": {"name": "string", "email": "string"},
                    "response_schema": {"id": "string"},
                    "status_codes": [201, 400]
                }
            }
        }

        assert "/users" in artifacts.api_specs
        assert "GET" in artifacts.api_specs["/users"]

    def test_database_schema_tracking(self):
        """Test database schema in architecture."""
        artifacts = ArchitectureArtifacts()
        artifacts.database_schema = "users(id, name, email), posts(id, user_id, content)"

        assert "users" in artifacts.database_schema
        assert "posts" in artifacts.database_schema

    def test_design_system_specification(self):
        """Test design system in architecture."""
        artifacts = ArchitectureArtifacts()
        artifacts.design_system = {
            "colors": {
                "primary": "#007bff",
                "secondary": "#6c757d"
            },
            "typography": {
                "h1": {"size": "32px", "weight": "bold"},
                "body": {"size": "16px", "weight": "regular"}
            },
            "spacing": {
                "xs": "4px",
                "sm": "8px",
                "md": "16px"
            }
        }

        assert artifacts.design_system["colors"]["primary"] == "#007bff"
        assert artifacts.design_system["typography"]["h1"]["size"] == "32px"

    def test_critical_sections_tracking(self):
        """Test critical sections designation."""
        artifacts = ArchitectureArtifacts()
        artifacts.critical_sections = {
            "UserAuthentication": "full",
            "PaymentProcessing": "full",
            "NotificationService": "summary",
            "Analytics": "summary"
        }

        assert artifacts.critical_sections["UserAuthentication"] == "full"
        assert artifacts.critical_sections["Analytics"] == "summary"


@pytest.mark.unit
class TestDevelopmentArtifactSchema:
    """Test Development Agent artifact schema validation."""

    def test_code_files_schema(self):
        """Test code files schema."""
        artifacts = DevelopmentArtifacts()
        artifacts.code_files = {
            "src/index.ts": "// Entry point",
            "src/components/App.tsx": "// App component",
            "src/styles/index.css": "/* Global styles */"
        }

        assert len(artifacts.code_files) == 3
        assert "src/index.ts" in artifacts.code_files

    def test_types_schema(self):
        """Test TypeScript types schema."""
        artifacts = DevelopmentArtifacts()
        artifacts.types = {
            "src/types/User.ts": "interface User { id: string; name: string; }",
            "src/types/Post.ts": "interface Post { id: string; userId: string; }"
        }

        assert len(artifacts.types) == 2

    def test_tests_schema(self):
        """Test test files schema."""
        artifacts = DevelopmentArtifacts()
        artifacts.tests = {
            "src/__tests__/App.test.tsx": "describe('App', () => {})",
            "src/__tests__/utils.test.ts": "describe('Utils', () => {})"
        }

        assert len(artifacts.tests) == 2

    def test_development_status(self):
        """Test development artifact status field."""
        artifacts = DevelopmentArtifacts()

        assert artifacts.status == TaskStatus.PENDING

        artifacts.status = TaskStatus.IN_PROGRESS
        assert artifacts.status == TaskStatus.IN_PROGRESS

        artifacts.status = TaskStatus.COMPLETED
        assert artifacts.status == TaskStatus.COMPLETED

    def test_development_dependencies(self):
        """Test version dependencies in development artifacts."""
        artifacts = DevelopmentArtifacts()
        artifacts.depends_on = {
            "architecture_001": 2,
            "planning_001": 1
        }

        assert artifacts.depends_on["architecture_001"] == 2
        assert len(artifacts.depends_on) == 2

    def test_summary_field(self):
        """Test summary field in development artifacts."""
        artifacts = DevelopmentArtifacts()
        artifacts.summary = "Implemented 8 components with 90% test coverage"

        assert "8 components" in artifacts.summary


@pytest.mark.unit
class TestTestingArtifactSchema:
    """Test QA Agent artifact schema validation."""

    def test_test_results_schema(self):
        """Test test results schema."""
        artifacts = TestingArtifacts()
        artifacts.test_results = {
            "total": 100,
            "passed": 95,
            "failed": 5,
            "skipped": 0,
            "coverage": 85.5,
            "execution_time": 12.4
        }

        assert artifacts.test_results["passed"] == 95
        assert artifacts.test_results["coverage"] == 85.5

    def test_coverage_report_schema(self):
        """Test coverage report schema."""
        artifacts = TestingArtifacts()
        artifacts.coverage_report = {
            "overall": 85.5,
            "frontend": 88.2,
            "backend": 83.0,
            "by_file": {
                "App.tsx": 92.5,
                "api.py": 78.3
            }
        }

        assert artifacts.coverage_report["overall"] == 85.5
        assert artifacts.coverage_report["by_file"]["App.tsx"] == 92.5

    def test_bug_reports_schema(self):
        """Test bug reports schema."""
        artifacts = TestingArtifacts()
        artifacts.bug_reports = [
            {
                "bug_id": "BUG001",
                "title": "Login timeout",
                "severity": "high",
                "affected_component": "AuthService",
                "steps": ["Click login", "Wait 5 seconds"],
                "expected": "Should complete login",
                "actual": "Timeout error"
            },
            {
                "bug_id": "BUG002",
                "title": "Form validation",
                "severity": "medium",
                "affected_component": "UserForm"
            }
        ]

        assert len(artifacts.bug_reports) == 2
        assert artifacts.bug_reports[0]["severity"] == "high"

    def test_error_analysis_schema(self):
        """Test error analysis schema."""
        artifacts = TestingArtifacts()
        artifacts.error_analysis = {
            "root_causes": [
                "Missing error handling in API calls",
                "Race condition in state management"
            ],
            "patterns": [
                "API timeout",
                "Null reference exception"
            ],
            "affected_modules": ["backend", "frontend"],
            "recommendations": [
                "Add timeout handling",
                "Add synchronization"
            ]
        }

        assert len(artifacts.error_analysis["root_causes"]) == 2
        assert "API timeout" in artifacts.error_analysis["patterns"]

    def test_restart_plan_schema(self):
        """Test restart plan schema."""
        artifacts = TestingArtifacts()
        artifacts.restart_plan = {
            "restart_from_phase": "backend",
            "affected_agents": ["backend_dev", "data_modeler"],
            "tasks_to_redo": ["BT001", "BT002", "BT003"],
            "estimated_time_minutes": 45,
            "rationale": "Database schema redesign needed",
            "impact_analysis": {
                "frontend_affected": False,
                "testing_needed": True,
                "docs_update_needed": False
            }
        }

        assert artifacts.restart_plan["restart_from_phase"] == "backend"
        assert len(artifacts.restart_plan["tasks_to_redo"]) == 3
        assert artifacts.restart_plan["impact_analysis"]["testing_needed"] is True

    def test_affected_agents_tracking(self):
        """Test affected agents tracking."""
        artifacts = TestingArtifacts()
        artifacts.affected_agents = ["backend_dev", "data_modeler"]

        assert "backend_dev" in artifacts.affected_agents
        assert len(artifacts.affected_agents) == 2


@pytest.mark.unit
class TestDocumentationArtifactSchema:
    """Test Documentation Agent artifact schema validation."""

    def test_readme_schema(self):
        """Test README schema."""
        artifacts = DocumentationArtifacts()
        artifacts.readme = """
# Project Name

## Overview
Description of the project.

## Installation
Steps to install.

## Usage
How to use.
"""

        assert "# Project Name" in artifacts.readme
        assert "Installation" in artifacts.readme

    def test_api_docs_schema(self):
        """Test API documentation schema."""
        artifacts = DocumentationArtifacts()
        artifacts.api_docs = """
## API Reference

### GET /api/users
Get all users.

**Response:**
```json
{
  "users": []
}
```

### POST /api/users
Create a new user.

**Request:**
```json
{
  "name": "string",
  "email": "string"
}
```
"""

        assert "GET /api/users" in artifacts.api_docs
        assert "Request" in artifacts.api_docs

    def test_architecture_docs_schema(self):
        """Test architecture documentation schema."""
        artifacts = DocumentationArtifacts()
        artifacts.architecture_docs = """
## System Architecture

### Components
- Frontend: React application
- Backend: FastAPI server
- Database: PostgreSQL

### Data Flow
1. User submits form in frontend
2. Frontend sends request to backend
3. Backend processes and returns response
"""

        assert "Components" in artifacts.architecture_docs
        assert "Frontend: React" in artifacts.architecture_docs

    def test_deployment_guide_schema(self):
        """Test deployment guide schema."""
        artifacts = DocumentationArtifacts()
        artifacts.deployment_guide = """
## Deployment Guide

### Prerequisites
- Python 3.12+
- Node.js 22+
- PostgreSQL 16+

### Steps
1. Clone repository
2. Install dependencies
3. Configure environment
4. Deploy to production
"""

        assert "Prerequisites" in artifacts.deployment_guide
        assert "Python 3.12" in artifacts.deployment_guide

    def test_user_guide_schema(self):
        """Test user guide schema."""
        artifacts = DocumentationArtifacts()
        artifacts.user_guide = """
## User Guide

### Getting Started
1. Sign up for an account
2. Create a profile
3. Start using the app

### Features
- Feature 1
- Feature 2
- Feature 3
"""

        assert "Getting Started" in artifacts.user_guide
        assert "Feature 1" in artifacts.user_guide


@pytest.mark.unit
class TestArtifactMetadata:
    """Test artifact metadata schema."""

    def test_artifact_metadata_schema(self):
        """Test complete artifact metadata schema."""
        metadata = ArtifactMetadata(
            artifact_name="requirements.md",
            artifact_type="requirements",
            size_bytes=2048,
            version=1,
            relevance_tags=["planning", "requirements"],
            compression_ratio=1.0
        )

        assert metadata.artifact_name == "requirements.md"
        assert metadata.artifact_type == "requirements"
        assert "planning" in metadata.relevance_tags

    def test_artifact_manifest_schema(self):
        """Test artifact manifest schema."""
        manifest = ArtifactManifest()

        meta1 = ArtifactMetadata(
            artifact_name="requirements.md",
            artifact_type="requirements",
            size_bytes=2048
        )
        meta2 = ArtifactMetadata(
            artifact_name="components.json",
            artifact_type="component_specs",
            size_bytes=4096
        )

        manifest.register_artifact("req", meta1)
        manifest.register_artifact("comp", meta2)

        assert len(manifest.artifacts) == 2
        assert manifest.get_artifact_info("req") == meta1


@pytest.mark.unit
class TestAgentMessageSchema:
    """Test agent message schema for artifact handoff."""

    def test_agent_message_schema(self):
        """Test agent message with artifacts."""
        message = AgentMessage(
            agent_id="planning_001",
            role="Planning Agent",
            content="Planning phase complete",
            artifacts={
                "requirements": "Detailed requirements",
                "tasks": [
                    {"task_id": "T001", "title": "Task 1"},
                    {"task_id": "T002", "title": "Task 2"}
                ],
                "complexity_score": 55
            }
        )

        assert message.agent_id == "planning_001"
        assert "requirements" in message.artifacts
        assert len(message.artifacts["tasks"]) == 2

    def test_message_handoff_chain(self):
        """Test message handoff between agents."""
        # Planning message
        planning_msg = AgentMessage(
            agent_id="planning_001",
            role="Planning Agent",
            content="Planning complete",
            artifacts={"requirements": "Test"}
        )

        # Architecture message builds on planning
        arch_msg = AgentMessage(
            agent_id="arch_001",
            role="Architecture Agent",
            content="Architecture designed",
            artifacts={
                "system_design": "Design",
                "planning_reference": planning_msg.artifacts["requirements"]
            }
        )

        # Verify chain
        assert arch_msg.artifacts["planning_reference"] == "Test"


@pytest.mark.unit
class TestSchemaVersioning:
    """Test schema versioning and backward compatibility."""

    def test_artifact_versioning(self):
        """Test artifact version tracking."""
        meta_v1 = ArtifactMetadata(
            artifact_name="spec.json",
            artifact_type="specs",
            size_bytes=1000,
            version=1
        )

        meta_v2 = ArtifactMetadata(
            artifact_name="spec.json",
            artifact_type="specs",
            size_bytes=1500,
            version=2
        )

        assert meta_v1.version == 1
        assert meta_v2.version == 2

    def test_optional_fields_backward_compat(self):
        """Test backward compatibility with optional fields."""
        # Minimal artifact
        minimal = PlanningArtifacts()
        assert minimal.summary is None
        assert minimal.tech_stack is None

        # Extended artifact
        extended = PlanningArtifacts(
            summary="Test summary",
            tech_stack={"frontend": "React"}
        )
        assert extended.summary == "Test summary"
        assert extended.tech_stack["frontend"] == "React"
