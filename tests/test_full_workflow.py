"""
End-to-end workflow tests for complete project lifecycle.

Tests cover:
- Simple project (todo app) without specialists
- Complex project (e-commerce) with all specialists
- High-performance project with performance specialist
- Error recovery and restart workflows
- Final state consistency and artifact verification
"""

import pytest
from state_models import (
    AgentState,
    AgentPhase,
    TaskStatus,
    ExecutionStatus,
    AgentMessage,
    PlanningArtifacts,
    ArchitectureArtifacts,
    DevelopmentArtifacts,
    DevelopmentSection,
    TestingArtifacts,
    DocumentationArtifacts,
    create_initial_state,
    apply_state_update,
    StateUpdate,
)
from orchestrator.specialist_agent_selector import (
    ComplexityFactors,
    create_default_selector,
)


@pytest.mark.e2e
class TestSimpleProjectWorkflow:
    """End-to-end test for simple project (todo app)."""

    def test_simple_todo_app_complete_workflow(self):
        """Test complete workflow for simple todo app."""
        # Step 1: Initialize project
        state = create_initial_state(
            project_id="simple_todo_e2e_001",
            user_request="Build a simple todo list application with React and FastAPI",
            tech_stack={"frontend": "React", "backend": "FastAPI"}
        )

        assert state.metadata.project_id == "simple_todo_e2e_001"
        assert state.metadata.current_phase == AgentPhase.PLANNING

        # Step 2: Planning phase
        planning_update = StateUpdate(
            planning_artifacts=PlanningArtifacts(
                requirements=(
                    "Build a simple todo app with: "
                    "1. Add/edit/delete todos "
                    "2. Mark todos as complete "
                    "3. Persistent storage"
                ),
                complexity_score=35,
                complexity_factors=["api", "ui_heavy"],
                tasks=[
                    {"task_id": "T001", "title": "Design Architecture", "status": "pending"},
                    {"task_id": "T002", "title": "Implement Frontend", "status": "pending"},
                    {"task_id": "T003", "title": "Implement Backend", "status": "pending"},
                    {"task_id": "T004", "title": "Test", "status": "pending"},
                    {"task_id": "T005", "title": "Documentation", "status": "pending"},
                ],
                dependencies={"T002": ["T001"], "T003": ["T001"]},
                risks=["Simple deployment needed", "SQLite database suitable"]
            ),
            current_phase=AgentPhase.ARCHITECTURE,
            message=AgentMessage(
                agent_id="planning_001",
                role="Planning Agent",
                content="Planning complete. Simple project - no specialists needed."
            )
        )
        state = apply_state_update(state, planning_update)

        assert state.planning_artifacts.complexity_score == 35
        assert state.metadata.current_phase == AgentPhase.ARCHITECTURE

        # Verify no specialists needed for simple project
        factors = ComplexityFactors(
            has_api=True,
            has_ui_heavy=True,
            component_count=8,
            table_count=2,
            api_endpoint_count=4
        )
        selector = create_default_selector()
        specialists = selector.select_specialists(35, factors)
        assert len(specialists) <= 1  # Minimal or no specialists

        # Step 3: Architecture phase
        from artifact_schemas import ComponentSpec, APIEndpoint
        arch_update = StateUpdate(
            architecture_artifacts=ArchitectureArtifacts(
                system_design="Simple monolithic architecture: React frontend + FastAPI backend + SQLite",
                component_specs={
                    "TodoApp": ComponentSpec(
                        name="TodoApp", description="Root todo application",
                        props={"todos": "list"}, state=["todos", "loading"],
                    ),
                    "TodoList": ComponentSpec(
                        name="TodoList", description="Renders the todo list",
                        props={"todos": "list", "onDelete": "callable"},
                    ),
                    "TodoItem": ComponentSpec(
                        name="TodoItem", description="Renders a single todo item",
                        props={"todo": "dict", "onComplete": "callable", "onDelete": "callable"},
                    ),
                },
                api_specs={
                    "/api/todos-get": APIEndpoint(path="/api/todos", method="GET", description="List todos"),
                    "/api/todos-post": APIEndpoint(path="/api/todos", method="POST", description="Create todo"),
                    "/api/todos-put": APIEndpoint(path="/api/todos/{id}", method="PUT", description="Update todo"),
                    "/api/todos-delete": APIEndpoint(path="/api/todos/{id}", method="DELETE", description="Delete todo"),
                },
                database_schema="todos(id, title, completed, created_at)"
            ),
            current_phase=AgentPhase.FRONTEND,
            message=AgentMessage(
                agent_id="arch_001",
                role="Architecture Agent",
                content="Architecture designed. 3 components, 4 endpoints, simple schema."
            )
        )
        state = apply_state_update(state, arch_update)

        assert len(state.architecture_artifacts.component_specs) == 3
        assert state.metadata.current_phase == AgentPhase.FRONTEND

        # Step 4: Frontend development
        frontend_update = StateUpdate(
            development=DevelopmentSection(
                frontend=DevelopmentArtifacts(
                    code_files={
                        "src/App.tsx": "// TodoApp component with state management",
                        "src/components/TodoList.tsx": "// List component",
                        "src/components/TodoItem.tsx": "// Item component",
                        "src/services/api.ts": "// API client"
                    },
                    tests={
                        "src/__tests__/App.test.tsx": "// App tests",
                    },
                    status=TaskStatus.COMPLETED
                ),
                backend=state.development.backend
            ),
            current_phase=AgentPhase.BACKEND
        )
        state = apply_state_update(state, frontend_update)

        assert len(state.development.frontend.code_files) == 4
        assert state.development.frontend.status == TaskStatus.COMPLETED

        # Step 5: Backend development
        backend_update = StateUpdate(
            development=DevelopmentSection(
                frontend=state.development.frontend,
                backend=DevelopmentArtifacts(
                    code_files={
                        "main.py": "# FastAPI app setup",
                        "models.py": "# SQLAlchemy models",
                        "schemas.py": "# Pydantic schemas",
                        "api/todos.py": "# Todo endpoints"
                    },
                    tests={
                        "tests/test_api.py": "# API tests",
                    },
                    status=TaskStatus.COMPLETED
                )
            ),
            current_phase=AgentPhase.QA
        )
        state = apply_state_update(state, backend_update)

        assert len(state.development.backend.code_files) == 4
        assert state.development.backend.status == TaskStatus.COMPLETED

        # Step 6: QA phase
        qa_update = StateUpdate(
            testing_artifacts=TestingArtifacts(
                test_results={
                    "total": 28,
                    "passed": 28,
                    "failed": 0,
                    "skipped": 0,
                    "coverage": 82.5,
                    "execution_time": 4.2
                },
                coverage_report={
                    "frontend": 85.0,
                    "backend": 80.0,
                    "overall": 82.5
                },
                bug_reports=[]  # No bugs for simple project
            ),
            current_phase=AgentPhase.DOCUMENTATION,
            message=AgentMessage(
                agent_id="qa_001",
                role="QA Agent",
                content="All tests passed! Coverage at 82.5%"
            )
        )
        state = apply_state_update(state, qa_update)

        assert state.testing_artifacts.test_results["passed"] == 28
        assert state.testing_artifacts.test_results["failed"] == 0

        # Step 7: Documentation phase
        doc_update = StateUpdate(
            documentation_artifacts=DocumentationArtifacts(
                readme="# Todo App\n\nA simple todo list application.",
                api_docs="## API Reference\n\n### GET /api/todos\nFetch all todos.",
                deployment_guide="## Deployment\n\n1. pip install -r requirements.txt",
                user_guide="## How to use\n\n1. Click Add Todo"
            ),
            current_phase=AgentPhase.COMPLETE,
            is_complete=True
        )
        state = apply_state_update(state, doc_update)

        # Step 8: Verify completion
        assert state.metadata.current_phase == AgentPhase.COMPLETE
        assert state.is_complete is True
        assert state.documentation_artifacts.readme is not None
        assert state.testing_artifacts.test_results["coverage"] == 82.5


@pytest.mark.e2e
class TestComplexProjectWorkflow:
    """End-to-end test for complex project (e-commerce platform)."""

    def test_ecommerce_platform_complete_workflow(self):
        """Test complete workflow for e-commerce platform with all specialists."""
        # Step 1: Initialize
        state = create_initial_state(
            project_id="ecom_e2e_001",
            user_request=(
                "Build a full-stack e-commerce platform with: "
                "user auth, product catalog, shopping cart, "
                "payment processing, order management, admin dashboard"
            ),
            tech_stack={"frontend": "React", "backend": "FastAPI", "database": "PostgreSQL"}
        )

        # Step 2: Planning
        planning_update = StateUpdate(
            planning_artifacts=PlanningArtifacts(
                requirements=(
                    "E-commerce platform with authentication, "
                    "product management, shopping cart, payments, orders"
                ),
                complexity_score=85,
                complexity_factors=[
                    "api", "database_heavy", "ui_heavy", "requires_auth",
                    "requires_compliance", "requires_scalability", "sensitive_data"
                ],
                tasks=[
                    {"task_id": "T001", "title": "Design", "status": "pending"},
                    {"task_id": "T002", "title": "Data Modeling", "status": "pending"},
                    {"task_id": "T003", "title": "API Design", "status": "pending"},
                    {"task_id": "T004", "title": "Security Review", "status": "pending"},
                    {"task_id": "T005", "title": "Frontend", "status": "pending"},
                    {"task_id": "T006", "title": "Backend", "status": "pending"},
                    {"task_id": "T007", "title": "Testing", "status": "pending"},
                    {"task_id": "T008", "title": "Docs", "status": "pending"},
                ]
            ),
            current_phase=AgentPhase.ARCHITECTURE
        )
        state = apply_state_update(state, planning_update)

        # Verify specialists would be selected
        factors = ComplexityFactors(
            has_api=True,
            has_microservices=True,
            has_ui_heavy=True,
            has_database_heavy=True,
            requires_auth=True,
            requires_compliance=True,
            requires_scalability=True,
            component_count=25,
            table_count=12,
            api_endpoint_count=30,
            sensitive_data_types=["PII", "Payment Info"]
        )
        selector = create_default_selector()
        specialists = selector.select_specialists(85, factors)
        assert len(specialists) >= 2  # Multiple specialists for complex project

        # Step 3: Architecture
        from artifact_schemas import ComponentSpec, APIEndpoint
        arch_update = StateUpdate(
            architecture_artifacts=ArchitectureArtifacts(
                system_design="Layered monolithic with clear separation of concerns",
                component_specs={
                    "UserDashboard": ComponentSpec(name="UserDashboard", description="User dashboard", props={"userId": "str"}),
                    "ProductCatalog": ComponentSpec(name="ProductCatalog", description="Product listing", props={"products": "list"}),
                    "ShoppingCart": ComponentSpec(name="ShoppingCart", description="Cart view", props={"items": "list"}),
                    "Checkout": ComponentSpec(name="Checkout", description="Checkout flow", props={"total": "float"}),
                    "OrderHistory": ComponentSpec(name="OrderHistory", description="Past orders", props={"orders": "list"}),
                    "AdminPanel": ComponentSpec(name="AdminPanel", description="Admin interface", props={"admin": "bool"}),
                },
                api_specs={
                    "/api/auth/login": APIEndpoint(path="/api/auth/login", method="POST", description="Login"),
                    "/api/users/{id}": APIEndpoint(path="/api/users/{id}", method="GET", description="Get user"),
                    "/api/products-get": APIEndpoint(path="/api/products", method="GET", description="List products"),
                    "/api/products-post": APIEndpoint(path="/api/products", method="POST", description="Create product"),
                    "/api/orders-get": APIEndpoint(path="/api/orders", method="GET", description="List orders"),
                    "/api/orders-post": APIEndpoint(path="/api/orders", method="POST", description="Create order"),
                    "/api/payments": APIEndpoint(path="/api/payments", method="POST", description="Process payment"),
                },
                database_schema=(
                    "users, products, orders, order_items, payments, "
                    "categories, reviews, admin_logs"
                ),
                critical_sections={
                    "UserAuthentication": "full",
                    "PaymentProcessing": "full",
                    "OrderManagement": "full",
                    "ProductCatalog": "summary"
                }
            ),
            current_phase=AgentPhase.FRONTEND
        )
        state = apply_state_update(state, arch_update)

        assert len(state.architecture_artifacts.component_specs) == 6

        # Step 4: Frontend (with specialist review)
        frontend_update = StateUpdate(
            development=DevelopmentSection(
                frontend=DevelopmentArtifacts(
                    code_files={
                        "src/pages/Dashboard.tsx": "// User dashboard",
                        "src/pages/Products.tsx": "// Product catalog",
                        "src/pages/Cart.tsx": "// Shopping cart",
                        "src/pages/Checkout.tsx": "// Checkout page",
                        "src/pages/Orders.tsx": "// Order history",
                        "src/pages/Admin.tsx": "// Admin panel",
                        "src/components/ProductCard.tsx": "// Product card",
                        "src/components/OrderItem.tsx": "// Order item",
                        "src/hooks/useAuth.ts": "// Auth hook",
                        "src/services/api.ts": "// API client",
                    },
                    status=TaskStatus.COMPLETED
                ),
                backend=state.development.backend
            ),
            current_phase=AgentPhase.BACKEND
        )
        state = apply_state_update(state, frontend_update)

        assert len(state.development.frontend.code_files) == 10

        # Step 5: Backend (with data modeler review)
        backend_update = StateUpdate(
            development=DevelopmentSection(
                frontend=state.development.frontend,
                backend=DevelopmentArtifacts(
                    code_files={
                        "main.py": "# FastAPI application",
                        "models/user.py": "# User model",
                        "models/product.py": "# Product model",
                        "models/order.py": "# Order model",
                        "models/payment.py": "# Payment model",
                        "api/auth.py": "# Authentication endpoints",
                        "api/products.py": "# Product endpoints",
                        "api/orders.py": "# Order endpoints",
                        "api/payments.py": "# Payment endpoints",
                        "services/auth_service.py": "# Auth service",
                        "services/payment_service.py": "# Payment service",
                    },
                    status=TaskStatus.COMPLETED
                )
            ),
            current_phase=AgentPhase.QA
        )
        state = apply_state_update(state, backend_update)

        assert len(state.development.backend.code_files) == 11

        # Step 6: QA
        qa_update = StateUpdate(
            testing_artifacts=TestingArtifacts(
                test_results={
                    "total": 145,
                    "passed": 138,
                    "failed": 7,
                    "coverage": 79.2
                },
                bug_reports=[
                    {"bug_id": "BUG001", "title": "Payment timeout issue", "severity": "high"},
                    {"bug_id": "BUG002", "title": "Cart sync lag", "severity": "medium"},
                    {"bug_id": "BUG003", "title": "Admin filter bug", "severity": "low"},
                ],
                error_analysis={
                    "root_causes": ["Race condition in payment", "Stale cart state"],
                    "affected_modules": ["backend", "frontend"]
                }
            ),
            current_phase=AgentPhase.DOCUMENTATION
        )
        state = apply_state_update(state, qa_update)

        assert state.testing_artifacts.test_results["failed"] == 7

        # Step 7: Documentation
        doc_update = StateUpdate(
            documentation_artifacts=DocumentationArtifacts(
                readme="# E-commerce Platform\n\nFull-stack e-commerce solution.",
                api_docs="## API Reference\n\nComplete API documentation.",
                architecture_docs="## Architecture\n\nSystem design and components.",
                deployment_guide="## Deployment\n\nProduction deployment guide.",
                user_guide="## User Guide\n\nHow to use the platform."
            ),
            current_phase=AgentPhase.COMPLETE,
            is_complete=True
        )
        state = apply_state_update(state, doc_update)

        # Verify completion
        assert state.is_complete is True
        assert state.testing_artifacts.test_results["passed"] == 138
        assert len(state.documentation_artifacts.readme) > 0


@pytest.mark.e2e
class TestHighPerformanceProjectWorkflow:
    """End-to-end test for high-performance project."""

    def test_realtime_analytics_platform(self):
        """Test workflow for real-time analytics platform."""
        # Initialize
        state = create_initial_state(
            project_id="analytics_e2e_001",
            user_request="Build a real-time analytics platform for 50k concurrent users"
        )

        # Planning
        planning_update = StateUpdate(
            planning_artifacts=PlanningArtifacts(
                complexity_score=82,
                complexity_factors=[
                    "api", "database_heavy", "real_time", "high_load",
                    "requires_performance", "requires_scalability"
                ]
            ),
            current_phase=AgentPhase.ARCHITECTURE
        )
        state = apply_state_update(state, planning_update)

        # Verify performance specialist would be selected
        factors = ComplexityFactors(
            has_api=True,
            has_real_time=True,
            has_high_load=True,
            requires_performance=True,
            requires_scalability=True,
            expected_concurrent_users=50000,
            global_user_base=True
        )
        selector = create_default_selector()
        specialists = selector.select_specialists(82, factors)
        performance_specialists = [
            s for s in specialists
            if "performance" in s.agent_id.lower()
        ]
        assert len(performance_specialists) > 0

        # Architecture with performance considerations
        arch_update = StateUpdate(
            architecture_artifacts=ArchitectureArtifacts(
                system_design="Distributed system with caching, message queues, and optimized databases",
                critical_sections={
                    "DataIngestion": "full",
                    "RealTimeProcessing": "full",
                    "Analytics": "summary"
                }
            ),
            current_phase=AgentPhase.FRONTEND
        )
        state = apply_state_update(state, arch_update)

        # Continue workflow...
        dev_update = StateUpdate(
            development=DevelopmentSection(
                frontend=DevelopmentArtifacts(
                    code_files={"src/Dashboard.tsx": "// Real-time dashboard"},
                    status=TaskStatus.COMPLETED
                ),
                backend=DevelopmentArtifacts(
                    code_files={
                        "main.py": "# FastAPI with async",
                        "services/analytics.py": "# Analytics service"
                    },
                    status=TaskStatus.COMPLETED
                )
            ),
            current_phase=AgentPhase.QA
        )
        state = apply_state_update(state, dev_update)

        # QA with performance metrics
        qa_update = StateUpdate(
            testing_artifacts=TestingArtifacts(
                test_results={
                    "total": 120,
                    "passed": 118,
                    "failed": 2,
                    "coverage": 81.0,
                    "load_test_tps": 15000,  # Throughput
                    "p99_latency_ms": 45  # 99th percentile latency
                }
            ),
            current_phase=AgentPhase.DOCUMENTATION
        )
        state = apply_state_update(state, qa_update)

        # Completion
        state.is_complete = True
        assert state.is_complete is True
        assert state.testing_artifacts.test_results["load_test_tps"] == 15000


@pytest.mark.e2e
class TestErrorRecoveryWorkflow:
    """End-to-end test for error recovery and restart."""

    def test_recovery_from_backend_failure(self):
        """Test workflow recovery from backend failures."""
        # Initial progress through phases
        state = create_initial_state("recovery_e2e_001", "Test project")

        # Advance to QA
        state.metadata.current_phase = AgentPhase.QA
        state.development.frontend.code_files["App.tsx"] = "// Frontend code"
        state.development.backend.code_files["main.py"] = "# Backend code"

        # QA discovers critical backend issues
        qa_update = StateUpdate(
            testing_artifacts=TestingArtifacts(
                test_results={"total": 50, "passed": 30, "failed": 20},
                bug_reports=[
                    {"bug_id": "BUG001", "severity": "critical", "component": "backend"},
                    {"bug_id": "BUG002", "severity": "critical", "component": "backend"},
                ],
                error_analysis={
                    "root_causes": ["Invalid database schema design"],
                    "affected_modules": ["backend"]
                },
                restart_plan={
                    "restart_from_phase": "backend",
                    "affected_agents": ["backend_dev", "data_modeler"],
                    "estimated_time_minutes": 60,
                    "rationale": "Critical database schema issues"
                }
            )
        )
        state = apply_state_update(state, qa_update)

        # Verify restart plan is present
        assert state.testing_artifacts.restart_plan is not None
        assert state.testing_artifacts.restart_plan["restart_from_phase"] == "backend"

        # Recovery: Reset to backend phase with improved schema
        recovery_update = StateUpdate(
            current_phase=AgentPhase.BACKEND,
            development=DevelopmentSection(
                frontend=state.development.frontend,
                backend=DevelopmentArtifacts(
                    code_files={
                        "main.py": "# Improved backend",
                        "models.py": "# Corrected schema"
                    },
                    status=TaskStatus.IN_PROGRESS
                )
            )
        )
        state = apply_state_update(state, recovery_update)

        assert state.metadata.current_phase == AgentPhase.BACKEND

        # Re-test
        qa_retry_update = StateUpdate(
            testing_artifacts=TestingArtifacts(
                test_results={"total": 50, "passed": 50, "failed": 0}
            ),
            current_phase=AgentPhase.DOCUMENTATION,
            is_complete=True
        )
        state = apply_state_update(state, qa_retry_update)

        # Final verification
        assert state.is_complete is True
        assert state.testing_artifacts.test_results["failed"] == 0


@pytest.mark.e2e
class TestStateFinalVerification:
    """Final verification tests for complete workflows."""

    def test_final_state_consistency(self, simple_project_state):
        """Test final state consistency after complete workflow."""
        state = simple_project_state

        # Simulate all phases
        state.planning_artifacts.requirements = "Todo app"
        state.planning_artifacts.complexity_score = 35
        state.metadata.current_phase = AgentPhase.PLANNING

        state.architecture_artifacts.system_design = "Monolithic"
        state.metadata.current_phase = AgentPhase.ARCHITECTURE

        state.development.frontend.code_files["App.tsx"] = "// App"
        state.development.backend.code_files["main.py"] = "# API"
        state.metadata.current_phase = AgentPhase.QA

        state.testing_artifacts.test_results = {"passed": 50, "failed": 0}
        state.metadata.current_phase = AgentPhase.DOCUMENTATION

        state.documentation_artifacts.readme = "# App"
        state.is_complete = True

        # Verify structure
        assert state.planning_artifacts.requirements is not None
        assert len(state.development.frontend.code_files) > 0
        assert len(state.development.backend.code_files) > 0
        assert state.testing_artifacts.test_results is not None
        assert state.documentation_artifacts.readme is not None
        assert state.is_complete is True

    def test_artifact_generation_completeness(self):
        """Test that all expected artifacts are generated."""
        state = create_initial_state("complete_e2e_001", "Test")

        # Populate all sections
        state.planning_artifacts.requirements = "Req"
        state.architecture_artifacts.system_design = "Design"
        state.development.frontend.code_files["f.tsx"] = "F"
        state.development.backend.code_files["b.py"] = "B"
        state.testing_artifacts.test_results = {"passed": 10}
        state.documentation_artifacts.readme = "README"

        # Verify all sections have content
        assert state.planning_artifacts.requirements is not None
        assert state.architecture_artifacts.system_design is not None
        assert len(state.development.frontend.code_files) > 0
        assert len(state.development.backend.code_files) > 0
        assert state.testing_artifacts.test_results is not None
        assert state.documentation_artifacts.readme is not None
