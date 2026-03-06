"""
State models for Universal Agent Team.

Provides layered Pydantic models for agent state management with:
- Hierarchical organization (metadata, planning, architecture, development, testing, documentation)
- Section-based isolation for concurrent access
- Artifact versioning and dependency tracking
- Execution status with version management
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator


# ============================================================================
# Enums
# ============================================================================

class AgentPhase(str, Enum):
    """Agent execution phases."""
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    CONTRACT_VALIDATION = "contract_validation"
    FRONTEND = "frontend"
    BACKEND = "backend"
    QA = "qa"
    DOCUMENTATION = "documentation"
    COMPLETE = "complete"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ExecutionStatus(str, Enum):
    """Agent execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Message and Communication Models
# ============================================================================

class AgentMessage(BaseModel):
    """Message from an agent to orchestrator."""
    agent_id: str
    role: str
    content: str  # Human-readable summary
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ArtifactMetadata(BaseModel):
    """Metadata for an artifact."""
    artifact_name: str
    artifact_type: str  # "requirements", "api_specs", "code", "test", "docs", etc.
    full_location: Optional[str] = None  # External file path if > size threshold
    summary_location: str = "embedded"  # "embedded" or external path
    size_bytes: int
    version: int = 1
    relevance_tags: List[str] = Field(default_factory=list)
    compression_ratio: float = 1.0  # 1.0 = no compression, 0.15 = 15% of original
    in_state: bool = True  # Whether full content is in state or referenced externally
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArtifactManifest(BaseModel):
    """Manifest of all artifacts for context tracking."""
    artifacts: Dict[str, ArtifactMetadata] = Field(default_factory=dict)

    def register_artifact(self, name: str, artifact_meta: ArtifactMetadata):
        """Register an artifact in the manifest."""
        self.artifacts[name] = artifact_meta

    def get_artifact_info(self, name: str) -> Optional[ArtifactMetadata]:
        """Get metadata for an artifact."""
        return self.artifacts.get(name)


# ============================================================================
# Task Models
# ============================================================================

class TaskRecord(BaseModel):
    """Record of a task execution."""
    task_id: str
    agent_id: str
    phase: AgentPhase
    status: TaskStatus
    depends_on: List[str] = Field(default_factory=list)
    blocks: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = 0
    errors: List[str] = Field(default_factory=list)
    retry_count: int = 0


# ============================================================================
# Execution Status Models
# ============================================================================

class AgentExecutionStatus(BaseModel):
    """Execution status of a single agent."""
    agent_id: str
    status: ExecutionStatus
    version: int = 1  # Version of this agent's output
    depends_on: Dict[str, int] = Field(default_factory=dict)  # {agent_id: required_version}
    tests_passed: Optional[bool] = None
    last_executed_at: Optional[datetime] = None
    errors: List[str] = Field(default_factory=list)


class ExecutionStatusTracker(BaseModel):
    """Tracks execution status of all agents."""
    agents: Dict[str, AgentExecutionStatus] = Field(default_factory=dict)

    def update_agent_status(self, agent_id: str, status: ExecutionStatus, version: int = None):
        """Update an agent's execution status."""
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentExecutionStatus(
                agent_id=agent_id,
                status=status,
                version=1
            )
        else:
            self.agents[agent_id].status = status
            if version:
                self.agents[agent_id].version = version
            self.agents[agent_id].last_executed_at = datetime.now(timezone.utc)

    def get_agent_status(self, agent_id: str) -> Optional[AgentExecutionStatus]:
        """Get execution status of an agent."""
        return self.agents.get(agent_id)


# ============================================================================
# Artifact Models (Layered Section)
# ============================================================================

class PlanningArtifacts(BaseModel):
    """Artifacts produced by Planning Agent."""
    requirements: Optional[str] = None
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    risks: List[str] = Field(default_factory=list)
    summary: Optional[str] = None  # Compact summary for downstream agents
    tech_stack: Optional[Dict[str, Any]] = None  # {frontend, backend, detected_from}
    complexity_score: int = 50  # 1-100
    complexity_factors: List[str] = Field(default_factory=list)


class ArchitectureArtifacts(BaseModel):
    """Artifacts produced by Architecture Agent."""
    system_design: Optional[str] = None
    component_specs: Dict[str, Any] = Field(default_factory=dict)
    api_specs: Dict[str, Any] = Field(default_factory=dict)
    database_schema: Optional[str] = None
    design_system: Optional[str] = None
    deployment_templates: Optional[Dict[str, str]] = None
    summary: Optional[str] = None
    technology_decisions: Optional[Dict[str, Any]] = None  # {frontend_specialization, backend_specialization}
    critical_sections: Dict[str, Literal["full", "summary"]] = Field(default_factory=dict)


class DevelopmentArtifacts(BaseModel):
    """Artifacts for frontend and backend development."""
    code_files: Dict[str, str] = Field(default_factory=dict)  # {file_path: code}
    types: Optional[Dict[str, str]] = None
    tests: Optional[Dict[str, str]] = None
    summary: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    depends_on: Dict[str, int] = Field(default_factory=dict)  # {agent_id: required_version}


class DevelopmentSection(BaseModel):
    """Development section with isolated frontend and backend."""
    frontend: DevelopmentArtifacts = Field(default_factory=DevelopmentArtifacts)
    backend: DevelopmentArtifacts = Field(default_factory=DevelopmentArtifacts)
    contract_validation: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Validation results


class TestingArtifacts(BaseModel):
    """Artifacts produced by QA Agent."""
    test_results: Optional[Dict[str, Any]] = None
    coverage_report: Optional[Dict[str, Any]] = None
    bug_reports: List[Dict[str, Any]] = Field(default_factory=list)
    error_analysis: Optional[Dict[str, Any]] = None  # Root cause analysis
    restart_plan: Optional[Dict[str, Any]] = None  # Intelligent restart recommendations
    affected_agents: List[str] = Field(default_factory=list)
    summary: Optional[str] = None


class DocumentationArtifacts(BaseModel):
    """Artifacts produced by Documentation Agent."""
    readme: Optional[str] = None
    api_docs: Optional[str] = None
    architecture_docs: Optional[str] = None
    deployment_guide: Optional[str] = None
    user_guide: Optional[str] = None
    summary: Optional[str] = None


# ============================================================================
# Metadata Models
# ============================================================================

class CompressionStats(BaseModel):
    """Statistics about state compression."""
    total_artifact_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 1.0
    tokens_saved: int = 0
    last_computed_at: Optional[datetime] = None


class ProjectMetadata(BaseModel):
    """Metadata about the project and state."""
    project_id: str
    user_request: str
    tech_stack: Optional[Dict[str, str]] = None
    complexity_score: int = 50
    current_phase: AgentPhase = AgentPhase.PLANNING
    current_agent: Optional[str] = None
    artifact_manifest: ArtifactManifest = Field(default_factory=ArtifactManifest)
    compression_stats: CompressionStats = Field(default_factory=CompressionStats)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Main Agent State Model (Hierarchical)
# ============================================================================

class AgentState(BaseModel):
    """
    Hierarchical agent state with section-based isolation.

    Structure:
    - metadata: Project and tracking information
    - planning_artifacts: From Planning Agent
    - architecture_artifacts: From Architecture Agent
    - development: Frontend/Backend (isolated sections)
    - testing_artifacts: From QA Agent
    - documentation_artifacts: From Documentation Agent
    - execution_status: Version tracking for all agents
    - messages: Communication history
    - errors: Error log
    - requires_human_approval: Flag for pauses
    """

    # ====== Metadata Section ======
    metadata: ProjectMetadata = Field(default_factory=ProjectMetadata)

    # ====== Artifact Sections ======
    planning_artifacts: PlanningArtifacts = Field(default_factory=PlanningArtifacts)
    architecture_artifacts: ArchitectureArtifacts = Field(default_factory=ArchitectureArtifacts)
    development: DevelopmentSection = Field(default_factory=DevelopmentSection)
    testing_artifacts: TestingArtifacts = Field(default_factory=TestingArtifacts)
    documentation_artifacts: DocumentationArtifacts = Field(default_factory=DocumentationArtifacts)

    # ====== Execution Tracking ======
    execution_status: ExecutionStatusTracker = Field(default_factory=ExecutionStatusTracker)
    tasks: List[TaskRecord] = Field(default_factory=list)

    # ====== Communication & Error Handling ======
    messages: List[AgentMessage] = Field(
        default_factory=list,
        max_items=10000,  # Reasonable max for long workflows
        description="Agent execution messages (max 10000)"
    )
    errors: List[str] = Field(
        default_factory=list,
        max_items=1000,  # Keep errors more limited
        description="Error messages (max 1000)"
    )
    retry_count: int = 0

    # ====== Human Interaction ======
    requires_human_approval: bool = False
    approval_reason: Optional[str] = None
    next_agent: Optional[str] = None
    is_complete: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    # ====== Convenience Methods ======

    def add_message(self, message: AgentMessage):
        """Add a message to the communication history with size check."""
        if len(self.messages) >= 10000:
            # Remove oldest message to make room
            self.messages.pop(0)
        self.messages.append(message)
        self.metadata.last_modified_at = datetime.now(timezone.utc)

    def add_error(self, error: str):
        """Add an error to the error log with size check."""
        if len(self.errors) >= 1000:
            # Remove oldest error to make room
            self.errors.pop(0)
        self.errors.append(error)
        self.metadata.last_modified_at = datetime.now(timezone.utc)

    def mark_phase_complete(self, phase: AgentPhase, next_phase: Optional[AgentPhase] = None):
        """Mark a phase as complete and set next phase."""
        self.metadata.current_phase = next_phase or phase
        self.metadata.last_modified_at = datetime.now(timezone.utc)

    def create_task_record(self, task_id: str, agent_id: str, phase: AgentPhase) -> TaskRecord:
        """Create a task record."""
        task = TaskRecord(
            task_id=task_id,
            agent_id=agent_id,
            phase=phase,
            status=TaskStatus.PENDING
        )
        self.tasks.append(task)
        return task

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_artifacts_by_section(self, section: str) -> Dict[str, Any]:
        """Get all artifacts from a section."""
        sections = {
            "planning": self.planning_artifacts.model_dump(),
            "architecture": self.architecture_artifacts.model_dump(),
            "development_frontend": self.development.frontend.model_dump(),
            "development_backend": self.development.backend.model_dump(),
            "testing": self.testing_artifacts.model_dump(),
            "documentation": self.documentation_artifacts.model_dump()
        }
        return sections.get(section, {})


# ============================================================================
# State Update Model (for agent responses)
# ============================================================================

class StateUpdate(BaseModel):
    """
    Update to apply to AgentState.

    Agents return this to indicate what state changes to make.
    The orchestrator applies these updates to the state.
    """
    # Artifact updates (optional)
    planning_artifacts: Optional[PlanningArtifacts] = None
    architecture_artifacts: Optional[ArchitectureArtifacts] = None
    development: Optional[DevelopmentSection] = None
    testing_artifacts: Optional[TestingArtifacts] = None
    documentation_artifacts: Optional[DocumentationArtifacts] = None

    # Metadata updates
    current_phase: Optional[AgentPhase] = None
    current_agent: Optional[str] = None
    next_agent: Optional[str] = None

    # Communication
    message: Optional[AgentMessage] = None
    errors: List[str] = Field(default_factory=list)

    # Status updates
    task_id: Optional[str] = None
    task_status: Optional[TaskStatus] = None

    # Control flow
    requires_human_approval: bool = False
    approval_reason: Optional[str] = None
    is_complete: bool = False


# ============================================================================
# Convenience Functions
# ============================================================================

def create_initial_state(
    project_id: str,
    user_request: str,
    tech_stack: Optional[Dict[str, str]] = None
) -> AgentState:
    """
    Create an initial AgentState for a new project.

    Args:
        project_id: Unique project identifier
        user_request: User's project description
        tech_stack: Optional technology stack {frontend, backend}

    Returns:
        Initialized AgentState
    """
    metadata = ProjectMetadata(
        project_id=project_id,
        user_request=user_request,
        tech_stack=tech_stack,
        current_phase=AgentPhase.PLANNING
    )

    return AgentState(metadata=metadata)


def apply_state_update(state: AgentState, update: StateUpdate) -> AgentState:
    """
    Apply a StateUpdate to an AgentState with validation.

    Args:
        state: Current state
        update: Update to apply

    Returns:
        Updated state

    Raises:
        ValueError: If state becomes invalid after update
    """
    import logging
    logger = logging.getLogger(__name__)

    if update.planning_artifacts:
        state.planning_artifacts = update.planning_artifacts

    if update.architecture_artifacts:
        state.architecture_artifacts = update.architecture_artifacts

    if update.development:
        state.development = update.development

    if update.testing_artifacts:
        state.testing_artifacts = update.testing_artifacts

    if update.documentation_artifacts:
        state.documentation_artifacts = update.documentation_artifacts

    if update.current_phase:
        state.metadata.current_phase = update.current_phase

    if update.current_agent:
        state.metadata.current_agent = update.current_agent

    if update.next_agent:
        state.next_agent = update.next_agent

    if update.message:
        state.add_message(update.message)

    if update.errors:
        for error in update.errors:
            state.add_error(error)

    if update.task_id and update.task_status:
        task = state.get_task(update.task_id)
        if task:
            task.status = update.task_status

    if update.requires_human_approval:
        state.requires_human_approval = True
        state.approval_reason = update.approval_reason

    if update.is_complete:
        state.is_complete = True

    state.metadata.last_modified_at = datetime.now(timezone.utc)

    # Validate state before returning
    try:
        state.model_validate(state.model_dump())
        logger.debug("State validation passed after update")
    except Exception as e:
        logger.error(f"State validation failed: {e}")
        raise ValueError(f"Invalid state after update: {e}") from e

    return state
