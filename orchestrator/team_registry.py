"""
Team registry for managing agent team configurations.

Teams are shared across all projects. A team specifies:
- Which agents are available
- Their specifications (from /workspace/agents/)
- Dependency relationships between agents
- Configuration for orchestration

Uses BaseRegistry for caching and persistence (Quick Win 3).
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from orchestrator.base_registry import BaseRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# Team Configuration Models
# ============================================================================

class AgentSpec(BaseModel):
    """Specification for an agent in a team."""
    agent_id: str = Field(..., description="Unique agent identifier")
    role: str = Field(..., description="Agent's role (planning, architecture, etc.)")
    spec_file: str = Field(..., description="Path to agent spec file")
    description: Optional[str] = None
    specializations: List[str] = Field(
        default_factory=list,
        description="Available specializations for this agent"
    )


class TeamConfig(BaseModel):
    """Configuration for an agent team."""
    team_id: str = Field(..., description="Unique team identifier")
    name: str = Field(..., description="Human-readable team name")
    description: Optional[str] = None
    spec_location: str = Field(..., description="Base location of agent specs")
    agents: List[AgentSpec] = Field(default_factory=list)

    # Dependencies: {agent_id: [depends_on_agent_ids]}
    dependencies: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Agent dependencies"
    )

    # Configuration
    allow_parallel_execution: bool = Field(
        default=True,
        description="Whether to allow parallel agent execution"
    )
    max_retries: int = Field(default=3, description="Max retries per agent")
    checkpoint_enabled: bool = Field(
        default=True,
        description="Whether to enable checkpointing"
    )

    # Status
    active: bool = Field(default=True, description="Whether team is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Team Registry
# ============================================================================

class TeamRegistry(BaseRegistry[TeamConfig]):
    """
    Manages team configurations.

    Extends BaseRegistry for caching and persistence.
    Teams are stored in: ~/.claude/teams/[team_id]/
    Each team has:
    - team.json: Team configuration
    - agents.yaml: Agent list (optional, for reference)
    - dependencies.json: Dependency graph
    """

    REGISTRY_BASE = Path.home() / ".claude" / "teams"

    def __init__(self):
        """Initialize team registry."""
        super().__init__(str(TeamRegistry.REGISTRY_BASE))

    def _parse_config(self, data: dict) -> TeamConfig:
        """Parse raw data into TeamConfig."""
        return TeamConfig(**data)

    def _get_config_filename(self, key: str) -> str:
        """Get filename for a team key."""
        return f"{key}_team.json"

    def validate_config(self, config: TeamConfig) -> bool:
        """Validate team configuration.

        Args:
            config: TeamConfig to validate

        Returns:
            True if valid, False otherwise
        """
        # Call parent validation (Pydantic)
        if not super().validate_config(config):
            return False

        # Custom validation rules
        if not config.team_id or len(config.team_id.strip()) == 0:
            logger.error("team_id cannot be empty")
            return False

        if not config.name or len(config.name.strip()) == 0:
            logger.error("team name cannot be empty")
            return False

        if not config.agents or len(config.agents) == 0:
            logger.error("team must have at least one agent")
            return False

        # Validate dependencies reference only existing agents
        agent_ids = {agent.agent_id for agent in config.agents}
        for agent_id, deps in config.dependencies.items():
            if agent_id not in agent_ids:
                logger.error(f"Dependency references non-existent agent: {agent_id}")
                return False
            for dep in deps:
                if dep not in agent_ids:
                    logger.error(f"Agent {agent_id} depends on non-existent agent: {dep}")
                    return False

        return True

    @staticmethod
    def get_team_dir(team_id: str) -> Path:
        """Get directory for a team."""
        return TeamRegistry.REGISTRY_BASE / team_id

    @staticmethod
    def get_config_path(team_id: str) -> Path:
        """Get team config file path."""
        return TeamRegistry.get_team_dir(team_id) / "team.json"

    @staticmethod
    def get_dependencies_path(team_id: str) -> Path:
        """Get dependencies file path."""
        return TeamRegistry.get_team_dir(team_id) / "dependencies.json"

    @staticmethod
    def ensure_directories(team_id: str):
        """Ensure team directories exist."""
        TeamRegistry.get_team_dir(team_id).mkdir(parents=True, exist_ok=True)

    # Class-level instance for backward compatibility
    _instance: Optional['TeamRegistry'] = None

    @classmethod
    def _get_instance(cls) -> 'TeamRegistry':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def create_universal_team(
        cls,
        spec_location: str = "/workspace/agents"
    ) -> TeamConfig:
        """
        Create the universal-agents-v1 team.

        This is the default team using agents from /workspace/agents/

        Args:
            spec_location: Base location of agent specifications

        Returns:
            TeamConfig for universal team
        """
        team = TeamConfig(
            team_id="universal-agents-v1",
            name="Universal Agent Team v1",
            description="Default team with support for React + FastAPI, and other stacks",
            spec_location=spec_location,
            agents=[
                AgentSpec(
                    agent_id="planning",
                    role="planning",
                    spec_file=f"{spec_location}/01-planning-agent.md",
                    description="Analyze requirements and break into tasks"
                ),
                AgentSpec(
                    agent_id="architecture",
                    role="architecture",
                    spec_file=f"{spec_location}/02-architecture-agent.md",
                    description="Design system architecture and specs"
                ),
                AgentSpec(
                    agent_id="frontend",
                    role="frontend",
                    spec_file=f"{spec_location}/03-frontend-agent.md",
                    description="Generate frontend code",
                    specializations=["react", "react-native", "vue", "svelte"]
                ),
                AgentSpec(
                    agent_id="backend",
                    role="backend",
                    spec_file=f"{spec_location}/04-backend-agent.md",
                    description="Generate backend code",
                    specializations=["fastapi", "node-express", "django", "go"]
                ),
                AgentSpec(
                    agent_id="contract_validator",
                    role="validation",
                    spec_file=f"{spec_location}/07-contract-validator-agent.md",
                    description="Validate API contracts"
                ),
                AgentSpec(
                    agent_id="qa",
                    role="qa",
                    spec_file=f"{spec_location}/05-backtesting-qa-agent.md",
                    description="Test and validate code"
                ),
                AgentSpec(
                    agent_id="documentation",
                    role="documentation",
                    spec_file=f"{spec_location}/06-documentation-agent.md",
                    description="Generate documentation"
                ),
            ],
            dependencies={
                "planning": [],
                "architecture": ["planning"],
                "contract_validator": ["architecture"],
                "frontend": ["architecture", "contract_validator"],
                "backend": ["architecture", "contract_validator"],
                "qa": ["frontend", "backend"],
                "documentation": ["planning", "architecture", "frontend", "backend", "qa"]
            }
        )

        cls._get_instance().save("universal-agents-v1", team)
        return team

    def update(self, key: str, config: TeamConfig) -> bool:
        """Update team config and invalidate dependent caches.

        Args:
            key: Team identifier
            config: Updated team configuration

        Returns:
            True if update successful, False otherwise
        """
        success = self.save(key, config)

        if success:
            # Invalidate execution order cache when dependencies change
            from dependency_context import DependencyGraph
            DependencyGraph.invalidate_cache()
            logger.info(f"Team config updated: {key}, dependency caches invalidated")

        return success

    def delete_with_invalidation(self, key: str) -> bool:
        """Delete team and invalidate caches.

        Args:
            key: Team identifier

        Returns:
            True if delete successful, False otherwise
        """
        success = super().delete(key)

        if success:
            # Invalidate execution order cache when team is deleted
            from dependency_context import DependencyGraph
            DependencyGraph.invalidate_cache()
            logger.warning(f"Team deleted: {key}, dependency caches invalidated")

        return success

    @staticmethod
    def save_team_config(config: TeamConfig):
        """Save team config to disk (backward compatible)."""
        instance = TeamRegistry._get_instance()
        instance.update(config.team_id, config)

    @staticmethod
    def load_team_config(team_id: str) -> Optional[TeamConfig]:
        """
        Load team config from disk (backward compatible).

        Args:
            team_id: Team identifier

        Returns:
            TeamConfig if found, None otherwise
        """
        return TeamRegistry._get_instance().load(team_id)

    @staticmethod
    def get_all_teams() -> List[TeamConfig]:
        """Get all registered teams."""
        instance = TeamRegistry._get_instance()
        return list(instance.list_all().values())

    @staticmethod
    def team_exists(team_id: str) -> bool:
        """Check if a team exists."""
        return TeamRegistry._get_instance().exists(team_id)

    @staticmethod
    def get_team_dependencies(team_id: str) -> Optional[Dict[str, List[str]]]:
        """Get dependency graph for a team."""
        config = TeamRegistry.load_team_config(team_id)
        return config.dependencies if config else None

    @staticmethod
    def get_agent_spec(team_id: str, agent_id: str) -> Optional[AgentSpec]:
        """Get specification for an agent."""
        config = TeamRegistry.load_team_config(team_id)

        if not config:
            return None

        for agent in config.agents:
            if agent.agent_id == agent_id:
                return agent

        return None

    @staticmethod
    def ensure_universal_team():
        """Ensure universal team is registered. Create if missing."""
        if not TeamRegistry.team_exists("universal-agents-v1"):
            TeamRegistry.create_universal_team()
