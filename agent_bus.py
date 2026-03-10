"""
Agent Message Bus — thread-safe pub/sub for inter-agent communication.

Agents publish structured payloads to topics; the ContractValidator reads
frontend.api_calls and backend.api_routes to detect path mismatches and
auto-generate bug reports before QA runs.

Usage::

    from agent_bus import get_bus, reset_bus, ContractValidator

    # Reset at the start of each workflow run
    reset_bus()

    # Backend agent publishes its routes
    get_bus().publish(
        sender="backend_agent",
        topic="backend.api_routes",
        payload=[{"method": "POST", "path": "/auth/register"}, ...],
    )

    # Frontend agent publishes its calls
    get_bus().publish(
        sender="frontend_agent",
        topic="frontend.api_calls",
        payload=[{"method": "POST", "url": "/auth/register"}, ...],
    )

    # After both complete, validate contracts
    mismatch_bugs = ContractValidator().validate(get_bus())
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_bus")


# ---------------------------------------------------------------------------
# Message envelope
# ---------------------------------------------------------------------------

@dataclass
class BusMessage:
    """A message published to the bus."""
    sender: str
    topic: str
    payload: Any


# ---------------------------------------------------------------------------
# AgentMessageBus
# ---------------------------------------------------------------------------

class AgentMessageBus:
    """
    Thread-safe, in-process pub/sub bus.

    Topics used by the multi-agent system:
      - ``backend.api_routes``  — list of {"method": str, "path": str}
      - ``frontend.api_calls``  — list of {"method": str, "url": str}
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._messages: Dict[str, List[BusMessage]] = {}

    def publish(self, sender: str, topic: str, payload: Any) -> None:
        """
        Publish a message to a topic.

        Args:
            sender: Identifier of the publishing agent.
            topic: Topic string (e.g. "backend.api_routes").
            payload: Arbitrary data (list, dict, etc.).
        """
        msg = BusMessage(sender=sender, topic=topic, payload=payload)
        with self._lock:
            self._messages.setdefault(topic, []).append(msg)
        logger.debug(f"[Bus] {sender} → {topic}: {len(payload) if isinstance(payload, list) else payload}")

    def get(self, topic: str) -> List[BusMessage]:
        """Return all messages published to a topic (may be empty)."""
        with self._lock:
            return list(self._messages.get(topic, []))

    def get_latest_payload(self, topic: str) -> Optional[Any]:
        """Return the payload of the most recent message on a topic, or None."""
        messages = self.get(topic)
        return messages[-1].payload if messages else None

    def all_topics(self) -> List[str]:
        """Return all topics that have received at least one message."""
        with self._lock:
            return list(self._messages.keys())

    def clear(self) -> None:
        """Clear all messages (useful between tests)."""
        with self._lock:
            self._messages.clear()


# ---------------------------------------------------------------------------
# ContractValidator
# ---------------------------------------------------------------------------

class ContractValidator:
    """
    Validates API contracts between frontend and backend after parallel execution.

    Compares:
      - ``backend.api_routes`` — paths the backend actually implements
      - ``frontend.api_calls`` — URLs the frontend actually calls

    Generates critical-severity bug reports for each mismatch so the
    self-healing loop can instruct the dev agents to fix them.
    """

    def validate(self, bus: AgentMessageBus) -> List[Dict[str, Any]]:
        """
        Run contract validation and return a list of bug report dicts.

        Returns an empty list if no data is available on the bus or if
        all contracts are satisfied.
        """
        backend_routes = bus.get_latest_payload("backend.api_routes") or []
        frontend_calls = bus.get_latest_payload("frontend.api_calls") or []

        if not backend_routes and not frontend_calls:
            logger.info("[ContractValidator] No route data on bus — skipping contract check")
            return []

        if not backend_routes:
            logger.warning("[ContractValidator] No backend routes published — cannot validate")
            return []

        if not frontend_calls:
            logger.warning("[ContractValidator] No frontend API calls published — cannot validate")
            return []

        # Normalise backend routes: {"method": str, "path": str}
        backend_index: Dict[str, str] = {}  # normalised_path → method
        for route in backend_routes:
            if not isinstance(route, dict):
                continue
            path = self._normalise_path(route.get("path", ""))
            method = route.get("method", "GET").upper()
            backend_index[path] = method

        # Normalise frontend calls: {"method": str, "url": str}
        frontend_index: Dict[str, str] = {}  # normalised_path → method
        for call in frontend_calls:
            if not isinstance(call, dict):
                continue
            url = self._normalise_path(call.get("url", ""))
            method = call.get("method", "GET").upper()
            frontend_index[url] = method

        logger.info(
            f"[ContractValidator] Backend routes: {len(backend_index)}, "
            f"Frontend calls: {len(frontend_index)}"
        )

        bug_reports: List[Dict[str, Any]] = []
        bug_counter = 1

        # Frontend calls paths that backend doesn't expose
        for fe_path, fe_method in frontend_index.items():
            if fe_path not in backend_index:
                bug = {
                    "bug_id": f"CONTRACT_{bug_counter:03d}",
                    "severity": "critical",
                    "component": "api_contract",
                    "description": (
                        f"Frontend calls {fe_method} {fe_path} but backend does not expose this path. "
                        f"Available backend paths: {list(backend_index.keys())[:5]}"
                    ),
                    "suggested_fix": (
                        f"Add '{fe_method} {fe_path}' endpoint to the backend, "
                        f"OR update frontend to call an existing backend path."
                    ),
                }
                bug_reports.append(bug)
                bug_counter += 1
                logger.warning(f"[ContractValidator] MISMATCH: Frontend calls {fe_method} {fe_path} → not in backend")
            else:
                be_method = backend_index[fe_path]
                if be_method != fe_method:
                    bug = {
                        "bug_id": f"CONTRACT_{bug_counter:03d}",
                        "severity": "high",
                        "component": "api_contract",
                        "description": (
                            f"Method mismatch at {fe_path}: "
                            f"frontend uses {fe_method}, backend expects {be_method}."
                        ),
                        "suggested_fix": (
                            f"Change frontend to use {be_method} {fe_path}, "
                            f"OR update backend to accept {fe_method} {fe_path}."
                        ),
                    }
                    bug_reports.append(bug)
                    bug_counter += 1
                    logger.warning(
                        f"[ContractValidator] METHOD MISMATCH at {fe_path}: "
                        f"frontend={fe_method}, backend={be_method}"
                    )

        if bug_reports:
            logger.warning(
                f"[ContractValidator] {len(bug_reports)} contract violation(s) found"
            )
        else:
            logger.info("[ContractValidator] API contract validated — no mismatches")

        return bug_reports

    @staticmethod
    def _normalise_path(path: str) -> str:
        """
        Normalise an API path for comparison.

        Strips query strings, trailing slashes, and path parameters
        (replaces {param} and :param patterns with a placeholder).
        """
        # Drop query string
        path = path.split("?")[0]
        # Normalise trailing slash
        path = path.rstrip("/") or "/"
        # Ensure leading slash
        if path and not path.startswith("/"):
            path = "/" + path
        # Replace path parameters with {param}
        path = re.sub(r"\{[^}]+\}", "{param}", path)
        path = re.sub(r":[a-zA-Z_][a-zA-Z0-9_]*", "{param}", path)
        return path.lower()



# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_bus: Optional[AgentMessageBus] = None


def get_bus() -> AgentMessageBus:
    """Return the shared AgentMessageBus instance."""
    global _default_bus
    if _default_bus is None:
        _default_bus = AgentMessageBus()
    return _default_bus


def reset_bus() -> AgentMessageBus:
    """Create a fresh AgentMessageBus and set it as the singleton. Returns the new bus."""
    global _default_bus
    _default_bus = AgentMessageBus()
    logger.debug("[Bus] Bus reset")
    return _default_bus
