"""
Unit tests for agent_bus.py.

Tests cover:
- AgentMessageBus publish / get / get_latest_payload / all_topics / clear
- Thread-safety under concurrent publishes
- ContractValidator: no data, matching paths, path mismatch, method mismatch
- Path normalisation (_normalise_path)
- Module-level singleton (get_bus / reset_bus)
"""

import threading
from typing import List

import pytest

from agent_bus import (
    AgentMessageBus,
    BusMessage,
    ContractValidator,
    get_bus,
    reset_bus,
)


# ============================================================================
# AgentMessageBus basics
# ============================================================================

class TestAgentMessageBus:
    def setup_method(self):
        self.bus = AgentMessageBus()

    def test_publish_and_get(self):
        self.bus.publish("agent_a", "test.topic", {"key": "value"})
        messages = self.bus.get("test.topic")
        assert len(messages) == 1
        assert messages[0].sender == "agent_a"
        assert messages[0].topic == "test.topic"
        assert messages[0].payload == {"key": "value"}

    def test_get_returns_empty_for_unknown_topic(self):
        messages = self.bus.get("nonexistent.topic")
        assert messages == []

    def test_get_latest_payload(self):
        self.bus.publish("a", "my.topic", "first")
        self.bus.publish("b", "my.topic", "second")
        latest = self.bus.get_latest_payload("my.topic")
        assert latest == "second"

    def test_get_latest_payload_none_for_empty(self):
        result = self.bus.get_latest_payload("empty.topic")
        assert result is None

    def test_all_topics(self):
        self.bus.publish("a", "topic.one", [])
        self.bus.publish("b", "topic.two", [])
        topics = self.bus.all_topics()
        assert "topic.one" in topics
        assert "topic.two" in topics

    def test_clear_removes_all_messages(self):
        self.bus.publish("a", "topic.one", "data")
        self.bus.clear()
        assert self.bus.get("topic.one") == []
        assert self.bus.all_topics() == []

    def test_multiple_publishes_same_topic(self):
        for i in range(5):
            self.bus.publish(f"agent_{i}", "shared.topic", i)
        messages = self.bus.get("shared.topic")
        assert len(messages) == 5
        payloads = [m.payload for m in messages]
        assert payloads == [0, 1, 2, 3, 4]

    def test_get_returns_copy(self):
        self.bus.publish("a", "copy.topic", "data")
        msgs1 = self.bus.get("copy.topic")
        msgs2 = self.bus.get("copy.topic")
        assert msgs1 == msgs2
        assert msgs1 is not msgs2  # Different list objects


# ============================================================================
# Thread-safety
# ============================================================================

class TestAgentMessageBusThreadSafety:
    def test_concurrent_publishes(self):
        """Multiple threads publishing concurrently should not corrupt state."""
        bus = AgentMessageBus()
        errors: List[Exception] = []

        def publisher(thread_id: int):
            try:
                for i in range(20):
                    bus.publish(f"agent_{thread_id}", "concurrent.topic", (thread_id, i))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=publisher, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        messages = bus.get("concurrent.topic")
        assert len(messages) == 100  # 5 threads × 20 publishes

    def test_concurrent_reads_and_writes(self):
        bus = AgentMessageBus()
        errors: List[Exception] = []

        def writer():
            try:
                for i in range(10):
                    bus.publish("writer", "rw.topic", i)
            except Exception as exc:
                errors.append(exc)

        def reader():
            try:
                for _ in range(10):
                    bus.get("rw.topic")
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []


# ============================================================================
# ContractValidator
# ============================================================================

class TestContractValidator:
    def setup_method(self):
        self.bus = AgentMessageBus()
        self.validator = ContractValidator()

    def test_no_data_returns_empty(self):
        bugs = self.validator.validate(self.bus)
        assert bugs == []

    def test_only_backend_returns_empty(self):
        self.bus.publish("backend", "backend.api_routes", [
            {"method": "GET", "path": "/api/todos"}
        ])
        bugs = self.validator.validate(self.bus)
        assert bugs == []

    def test_only_frontend_returns_empty(self):
        self.bus.publish("frontend", "frontend.api_calls", [
            {"method": "GET", "url": "/api/todos"}
        ])
        bugs = self.validator.validate(self.bus)
        assert bugs == []

    def test_matching_paths_no_bugs(self):
        self.bus.publish("backend", "backend.api_routes", [
            {"method": "GET", "path": "/api/todos"},
            {"method": "POST", "path": "/api/todos"},
        ])
        self.bus.publish("frontend", "frontend.api_calls", [
            {"method": "GET", "url": "/api/todos"},
            {"method": "POST", "url": "/api/todos"},
        ])
        bugs = self.validator.validate(self.bus)
        assert bugs == []

    def test_path_mismatch_creates_critical_bug(self):
        self.bus.publish("backend", "backend.api_routes", [
            {"method": "GET", "path": "/api/todos"}
        ])
        self.bus.publish("frontend", "frontend.api_calls", [
            {"method": "GET", "url": "/api/items"}  # different path
        ])
        bugs = self.validator.validate(self.bus)
        assert len(bugs) == 1
        assert bugs[0]["severity"] == "critical"
        assert bugs[0]["component"] == "api_contract"
        assert "bug_id" in bugs[0]

    def test_method_mismatch_creates_high_severity_bug(self):
        self.bus.publish("backend", "backend.api_routes", [
            {"method": "POST", "path": "/api/todos"}
        ])
        self.bus.publish("frontend", "frontend.api_calls", [
            {"method": "GET", "url": "/api/todos"}  # wrong method
        ])
        bugs = self.validator.validate(self.bus)
        assert len(bugs) == 1
        assert bugs[0]["severity"] == "high"
        assert "/api/todos" in bugs[0]["description"]

    def test_multiple_mismatches(self):
        self.bus.publish("backend", "backend.api_routes", [
            {"method": "GET", "path": "/api/todos"},
        ])
        self.bus.publish("frontend", "frontend.api_calls", [
            {"method": "GET", "url": "/api/items"},
            {"method": "GET", "url": "/api/users"},
        ])
        bugs = self.validator.validate(self.bus)
        assert len(bugs) == 2
        assert all(b["severity"] == "critical" for b in bugs)

    def test_bug_ids_are_unique(self):
        self.bus.publish("backend", "backend.api_routes", [
            {"method": "GET", "path": "/a"},
        ])
        self.bus.publish("frontend", "frontend.api_calls", [
            {"method": "GET", "url": "/x"},
            {"method": "GET", "url": "/y"},
        ])
        bugs = self.validator.validate(self.bus)
        ids = [b["bug_id"] for b in bugs]
        assert len(ids) == len(set(ids))

    def test_suggested_fix_present(self):
        self.bus.publish("backend", "backend.api_routes", [
            {"method": "GET", "path": "/api/todos"}
        ])
        self.bus.publish("frontend", "frontend.api_calls", [
            {"method": "GET", "url": "/api/other"}
        ])
        bugs = self.validator.validate(self.bus)
        assert "suggested_fix" in bugs[0]
        assert len(bugs[0]["suggested_fix"]) > 0

    def test_invalid_route_entries_ignored(self):
        """Non-dict entries in routes/calls should not crash the validator."""
        self.bus.publish("backend", "backend.api_routes", [
            None, "invalid", {"method": "GET", "path": "/api/todos"}
        ])
        self.bus.publish("frontend", "frontend.api_calls", [
            None, {"method": "GET", "url": "/api/todos"}
        ])
        bugs = self.validator.validate(self.bus)
        assert bugs == []


# ============================================================================
# ContractValidator._normalise_path
# ============================================================================

class TestNormalisePath:
    def setup_method(self):
        self.v = ContractValidator()

    def test_trailing_slash_stripped(self):
        assert self.v._normalise_path("/api/todos/") == "/api/todos"

    def test_leading_slash_added(self):
        assert self.v._normalise_path("api/todos") == "/api/todos"

    def test_query_string_stripped(self):
        assert self.v._normalise_path("/api/todos?page=1&limit=10") == "/api/todos"

    def test_fastapi_path_params_normalised(self):
        assert self.v._normalise_path("/api/todos/{id}") == "/api/todos/{param}"

    def test_express_path_params_normalised(self):
        assert self.v._normalise_path("/api/todos/:id") == "/api/todos/{param}"

    def test_lowercase(self):
        assert self.v._normalise_path("/API/Todos") == "/api/todos"

    def test_root_path(self):
        assert self.v._normalise_path("/") == "/"

    def test_empty_path(self):
        result = self.v._normalise_path("")
        assert result == "/"


# ============================================================================
# Module-level singleton
# ============================================================================

class TestSingleton:
    def test_get_bus_returns_same_instance(self):
        bus1 = get_bus()
        bus2 = get_bus()
        assert bus1 is bus2

    def test_reset_bus_returns_new_instance(self):
        bus_before = get_bus()
        new_bus = reset_bus()
        bus_after = get_bus()
        assert new_bus is bus_after
        # The new instance should be different from the one before reset
        # (unless reset_bus was already called — check by publishing)
        new_bus.publish("test", "reset.topic", "ping")
        assert len(bus_after.get("reset.topic")) == 1

    def test_reset_clears_state(self):
        bus = get_bus()
        bus.publish("agent", "pre.reset.topic", "data")
        new_bus = reset_bus()
        # New bus should not have the old messages
        assert new_bus.get("pre.reset.topic") == []
