"""
Checkpoint manager for agent execution.

Implements streaming execution with intermediate checkpoints,
allowing agents to be interrupted and resumed without losing progress.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from state_models import AgentState, StateUpdate


# ============================================================================
# Checkpoint Model
# ============================================================================

class ExecutionCheckpoint:
    """Represents a checkpoint during agent execution."""

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        checkpoint_id: str,
        state_snapshot: Dict[str, Any],
        progress: int = 0,  # 0-100
        step_number: int = 0,
        is_complete: bool = False,
        error: Optional[str] = None
    ):
        self.project_id = project_id
        self.agent_id = agent_id
        self.checkpoint_id = checkpoint_id
        self.state_snapshot = state_snapshot
        self.progress = progress
        self.step_number = step_number
        self.is_complete = is_complete
        self.error = error
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary."""
        return {
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "checkpoint_id": self.checkpoint_id,
            "state_snapshot": self.state_snapshot,
            "progress": self.progress,
            "step_number": self.step_number,
            "is_complete": self.is_complete,
            "error": self.error,
            "created_at": self.created_at
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ExecutionCheckpoint":
        """Create checkpoint from dictionary."""
        return ExecutionCheckpoint(
            project_id=data["project_id"],
            agent_id=data["agent_id"],
            checkpoint_id=data["checkpoint_id"],
            state_snapshot=data["state_snapshot"],
            progress=data.get("progress", 0),
            step_number=data.get("step_number", 0),
            is_complete=data.get("is_complete", False),
            error=data.get("error", None)
        )


# ============================================================================
# Checkpoint Manager
# ============================================================================

class CheckpointManager:
    """
    Manages checkpoints for agent execution.

    Stores intermediate state snapshots to allow resuming interrupted
    agent execution.
    """

    # Checkpoint directory structure
    CHECKPOINT_BASE = Path.home() / ".claude" / "checkpoints"

    @staticmethod
    def get_checkpoint_dir(project_id: str) -> Path:
        """Get checkpoint directory for a project."""
        return CheckpointManager.CHECKPOINT_BASE / project_id

    @staticmethod
    def get_agent_checkpoint_dir(project_id: str, agent_id: str) -> Path:
        """Get checkpoint directory for an agent in a project."""
        return CheckpointManager.get_checkpoint_dir(project_id) / agent_id

    @staticmethod
    def ensure_directories(project_id: str):
        """Ensure checkpoint directories exist."""
        checkpoint_dir = CheckpointManager.get_checkpoint_dir(project_id)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def save_checkpoint(
        checkpoint: ExecutionCheckpoint,
        project_id: str
    ):
        """
        Save a checkpoint to disk.

        Args:
            checkpoint: Checkpoint to save
            project_id: Project ID
        """
        CheckpointManager.ensure_directories(project_id)

        agent_dir = CheckpointManager.get_agent_checkpoint_dir(project_id, checkpoint.agent_id)
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        checkpoint_file = agent_dir / f"checkpoint-{checkpoint.checkpoint_id}.json"

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

    @staticmethod
    def load_checkpoint(
        project_id: str,
        agent_id: str,
        checkpoint_id: str
    ) -> Optional[ExecutionCheckpoint]:
        """
        Load a checkpoint from disk.

        Args:
            project_id: Project ID
            agent_id: Agent ID
            checkpoint_id: Checkpoint ID

        Returns:
            Checkpoint if found, None otherwise
        """
        agent_dir = CheckpointManager.get_agent_checkpoint_dir(project_id, agent_id)
        checkpoint_file = agent_dir / f"checkpoint-{checkpoint_id}.json"

        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file, "r") as f:
            data = json.load(f)

        return ExecutionCheckpoint.from_dict(data)

    @staticmethod
    def get_latest_checkpoint(
        project_id: str,
        agent_id: str
    ) -> Optional[ExecutionCheckpoint]:
        """
        Get the most recent checkpoint for an agent.

        Args:
            project_id: Project ID
            agent_id: Agent ID

        Returns:
            Latest checkpoint if found, None otherwise
        """
        agent_dir = CheckpointManager.get_agent_checkpoint_dir(project_id, agent_id)

        if not agent_dir.exists():
            return None

        checkpoint_files = sorted(agent_dir.glob("checkpoint-*.json"))

        if not checkpoint_files:
            return None

        # Load latest checkpoint
        latest_file = checkpoint_files[-1]

        with open(latest_file, "r") as f:
            data = json.load(f)

        return ExecutionCheckpoint.from_dict(data)

    @staticmethod
    def clean_checkpoints(
        project_id: str,
        agent_id: str,
        keep_latest: int = 3
    ):
        """
        Clean old checkpoints, keeping only the most recent ones.

        Args:
            project_id: Project ID
            agent_id: Agent ID
            keep_latest: Number of latest checkpoints to keep
        """
        agent_dir = CheckpointManager.get_agent_checkpoint_dir(project_id, agent_id)

        if not agent_dir.exists():
            return

        checkpoint_files = sorted(agent_dir.glob("checkpoint-*.json"))

        # Remove all but the latest N
        if len(checkpoint_files) > keep_latest:
            for checkpoint_file in checkpoint_files[:-keep_latest]:
                checkpoint_file.unlink()

    @staticmethod
    def delete_all_checkpoints(project_id: str, agent_id: str = None):
        """
        Delete all checkpoints for a project or agent.

        Args:
            project_id: Project ID
            agent_id: Agent ID (if None, delete all for project)
        """
        if agent_id:
            agent_dir = CheckpointManager.get_agent_checkpoint_dir(project_id, agent_id)
            if agent_dir.exists():
                for checkpoint_file in agent_dir.glob("checkpoint-*.json"):
                    checkpoint_file.unlink()
                agent_dir.rmdir()
        else:
            project_dir = CheckpointManager.get_checkpoint_dir(project_id)
            if project_dir.exists():
                import shutil
                shutil.rmtree(project_dir)


# ============================================================================
# Streaming Execution Handler
# ============================================================================

class StreamingExecutionHandler:
    """
    Handles streaming agent execution with checkpoints.

    Allows agents to report progress and be interrupted/resumed.
    """

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        checkpoint_interval_seconds: int = 30
    ):
        self.project_id = project_id
        self.agent_id = agent_id
        self.checkpoint_interval = checkpoint_interval_seconds
        self.last_checkpoint_time = datetime.now(timezone.utc)
        self.step_number = 0
        self.checkpoint_counter = 0

    def should_checkpoint(self) -> bool:
        """Check if it's time to create a checkpoint."""
        elapsed = (datetime.now(timezone.utc) - self.last_checkpoint_time).total_seconds()
        return elapsed >= self.checkpoint_interval

    def create_checkpoint(
        self,
        state: AgentState,
        progress: int,
        is_complete: bool = False,
        error: Optional[str] = None
    ) -> ExecutionCheckpoint:
        """
        Create and save a checkpoint.

        Args:
            state: Current agent state
            progress: Progress percentage (0-100)
            is_complete: Whether agent execution is complete
            error: Any error that occurred

        Returns:
            Created checkpoint
        """
        self.checkpoint_counter += 1

        checkpoint = ExecutionCheckpoint(
            project_id=self.project_id,
            agent_id=self.agent_id,
            checkpoint_id=f"checkpoint-{self.checkpoint_counter:05d}",
            state_snapshot=state.model_dump(),
            progress=progress,
            step_number=self.step_number,
            is_complete=is_complete,
            error=error
        )

        CheckpointManager.save_checkpoint(checkpoint, self.project_id)
        self.last_checkpoint_time = datetime.now(timezone.utc)

        return checkpoint

    def get_resume_state(self) -> Optional[AgentState]:
        """
        Get the state to resume from (if agent was interrupted).

        Returns:
            AgentState to resume from, or None if starting fresh
        """
        latest_checkpoint = CheckpointManager.get_latest_checkpoint(
            self.project_id,
            self.agent_id
        )

        if latest_checkpoint and not latest_checkpoint.is_complete:
            # Resume from this checkpoint
            state_dict = latest_checkpoint.state_snapshot
            return AgentState(**state_dict)

        return None

    def mark_step(
        self,
        state: AgentState,
        step_description: str,
        progress: int
    ):
        """
        Mark completion of a step and potentially checkpoint.

        Args:
            state: Current state
            step_description: Description of completed step
            progress: Progress percentage (0-100)
        """
        self.step_number += 1

        if self.should_checkpoint():
            self.create_checkpoint(state, progress, is_complete=False)

    def mark_complete(
        self,
        state: AgentState,
        final_state_update: StateUpdate
    ):
        """
        Mark agent execution as complete.

        Args:
            state: Final state
            final_state_update: Final state update from agent
        """
        # Create final checkpoint
        checkpoint = self.create_checkpoint(
            state,
            progress=100,
            is_complete=True
        )

        # Clean up old checkpoints
        CheckpointManager.clean_checkpoints(self.project_id, self.agent_id)

        return checkpoint


# ============================================================================
# Execution Resume Helper
# ============================================================================

class ExecutionResumer:
    """Helps resume interrupted agent execution."""

    @staticmethod
    def can_resume(project_id: str, agent_id: str) -> bool:
        """Check if an agent can be resumed from checkpoint."""
        latest = CheckpointManager.get_latest_checkpoint(project_id, agent_id)
        return latest is not None and not latest.is_complete

    @staticmethod
    def resume_execution(
        project_id: str,
        agent_id: str
    ) -> Optional[AgentState]:
        """
        Resume execution from the latest checkpoint.

        Args:
            project_id: Project ID
            agent_id: Agent ID

        Returns:
            State to resume from, or None if nothing to resume
        """
        latest = CheckpointManager.get_latest_checkpoint(project_id, agent_id)

        if not latest or latest.is_complete:
            return None

        # Reconstruct state from checkpoint
        state_dict = latest.state_snapshot
        return AgentState(**state_dict)

    @staticmethod
    def get_resume_info(project_id: str, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a resumable checkpoint.

        Args:
            project_id: Project ID
            agent_id: Agent ID

        Returns:
            Information about resumable checkpoint, or None
        """
        latest = CheckpointManager.get_latest_checkpoint(project_id, agent_id)

        if not latest or latest.is_complete:
            return None

        return {
            "checkpoint_id": latest.checkpoint_id,
            "progress": latest.progress,
            "step_number": latest.step_number,
            "created_at": latest.created_at,
            "error": latest.error
        }


# ============================================================================
# Checkpoint Statistics
# ============================================================================

class CheckpointStats:
    """Provides statistics about checkpoints."""

    @staticmethod
    def get_project_stats(project_id: str) -> Dict[str, Any]:
        """Get checkpoint statistics for a project."""
        project_dir = CheckpointManager.get_checkpoint_dir(project_id)

        if not project_dir.exists():
            return {}

        stats = {}

        for agent_dir in project_dir.iterdir():
            if agent_dir.is_dir():
                agent_id = agent_dir.name
                checkpoints = list(agent_dir.glob("checkpoint-*.json"))

                stats[agent_id] = {
                    "checkpoint_count": len(checkpoints),
                    "latest_checkpoint": None,
                    "total_size_bytes": 0
                }

                if checkpoints:
                    latest = sorted(checkpoints)[-1]
                    latest_size = latest.stat().st_size

                    stats[agent_id]["latest_checkpoint"] = latest.name
                    stats[agent_id]["total_size_bytes"] = sum(
                        cp.stat().st_size for cp in checkpoints
                    )

        return stats

    @staticmethod
    def total_checkpoint_size(project_id: str) -> int:
        """Get total size of all checkpoints for a project."""
        stats = CheckpointStats.get_project_stats(project_id)
        return sum(
            agent_stats["total_size_bytes"]
            for agent_stats in stats.values()
        )
