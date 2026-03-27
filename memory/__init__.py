"""Memory layer for cross-run learning and context accumulation.

Provides:
- MemoryFact: Structured storage of facts extracted from agent runs
- MemoryContext: Pre-run context loaded from accumulated memory
- Observer Agents: Extract structured facts after each phase
- Search Agents: Retrieve relevant context before each run
- Local/Supermemory backends for flexible storage
"""

from memory.models import MemoryFact, MemoryContext, ObserverOutput
from memory.memory_manager import MemoryManager, get_memory_manager

__all__ = [
    "MemoryFact",
    "MemoryContext",
    "ObserverOutput",
    "MemoryManager",
    "get_memory_manager",
]
