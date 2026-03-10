"""
Unit tests for llm_client.py.

Tests cover:
- extract_json: fenced blocks, bare JSON, embedded JSON, truncation recovery
- _recover_truncated_json: bracket counting and recovery
- LLMClient.call: primary → fallback model logic (mocked API)
- Retry on transient errors and rate limits
- Circuit breaker: opens after CIRCUIT_OPEN_THRESHOLD failures
- Quota vs rate-limit wait time distinction
"""

import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch, call

import pytest

import llm_client as lc
from llm_client import (
    CircuitState,
    LLMClient,
    LLMResponse,
    PRIMARY_MODEL,
    FALLBACK_MODEL,
    CIRCUIT_OPEN_THRESHOLD,
    QUOTA_WAIT_SECONDS,
    BACKOFF_BASE,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_response(text: str) -> LLMResponse:
    return LLMResponse(
        content=text,
        model_used=PRIMARY_MODEL,
        input_tokens=10,
        output_tokens=20,
    )


def _make_client() -> LLMClient:
    """Return an LLMClient with a mocked underlying Anthropic client."""
    client = LLMClient.__new__(LLMClient)
    client._client = MagicMock()
    client.logger = MagicMock()
    return client


def _reset_circuits():
    """Reset all circuit breakers to closed state."""
    for state in lc._circuits.values():
        state.failures = 0
        state.opened_at = None


# ============================================================================
# extract_json — fenced code blocks
# ============================================================================

class TestExtractJsonFenced:
    def setup_method(self):
        self.client = _make_client()

    def test_json_fenced_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = self.client.extract_json(_make_response(text))
        assert result == {"key": "value"}

    def test_plain_fenced_block(self):
        text = '```\n{"key": "value"}\n```'
        result = self.client.extract_json(_make_response(text))
        assert result == {"key": "value"}

    def test_fenced_block_without_closing_backticks(self):
        text = '```json\n{"key": "value"}'
        result = self.client.extract_json(_make_response(text))
        assert result == {"key": "value"}

    def test_fenced_block_with_prose_before(self):
        text = 'Here is my response:\n```json\n{"status": "ok"}\n```'
        result = self.client.extract_json(_make_response(text))
        assert result == {"status": "ok"}


# ============================================================================
# extract_json — bare JSON / embedded
# ============================================================================

class TestExtractJsonBare:
    def setup_method(self):
        self.client = _make_client()

    def test_bare_json_object(self):
        text = '{"name": "Alice", "age": 30}'
        result = self.client.extract_json(_make_response(text))
        assert result["name"] == "Alice"
        assert result["age"] == 30

    def test_nested_json(self):
        text = '{"outer": {"inner": {"deep": 42}}}'
        result = self.client.extract_json(_make_response(text))
        assert result["outer"]["inner"]["deep"] == 42

    def test_json_array_of_primitives(self):
        # extract_json checks { before [ in the scan loop.
        # Arrays of primitives work because there is no { to confuse the scanner.
        text = '[1, 2, 3]'
        result = self.client.extract_json(_make_response(text))
        assert result == [1, 2, 3]

    def test_json_object_containing_array(self):
        # The idiomatic way to return a list from an LLM is wrapped in an object.
        text = '{"items": [{"id": 1}, {"id": 2}]}'
        result = self.client.extract_json(_make_response(text))
        assert len(result["items"]) == 2
        assert result["items"][0]["id"] == 1

    def test_json_with_whitespace(self):
        text = '  \n  {"key":   "value"  }  \n  '
        result = self.client.extract_json(_make_response(text))
        assert result["key"] == "value"


# ============================================================================
# extract_json — truncation recovery
# ============================================================================

class TestExtractJsonRecovery:
    def setup_method(self):
        self.client = _make_client()

    def test_truncated_missing_closing_brace(self):
        text = '{"key": "value"'
        result = self.client.extract_json(_make_response(text))
        assert result["key"] == "value"

    def test_truncated_nested_missing_braces(self):
        text = '{"outer": {"inner": "data"'
        result = self.client.extract_json(_make_response(text))
        assert result["outer"]["inner"] == "data"

    def test_invalid_json_raises(self):
        text = "This is plain text with no JSON at all."
        with pytest.raises(ValueError, match="not valid JSON"):
            self.client.extract_json(_make_response(text))

    def test_truncated_in_string_value(self):
        text = '{"message": "hello world'
        result = self.client.extract_json(_make_response(text))
        assert "message" in result

    def test_truncated_object_with_nested_list(self):
        # Truncated JSON with a nested list — recovery should close open braces/brackets
        text = '{"items": [{"id": 1}, {"id": 2'
        result = self.client.extract_json(_make_response(text))
        assert "items" in result
        assert isinstance(result["items"], list)


# ============================================================================
# _recover_truncated_json
# ============================================================================

class TestRecoverTruncatedJson:
    def setup_method(self):
        self.client = _make_client()

    def test_complete_json_returns_parsed(self):
        text = '{"a": 1}'
        result = self.client._recover_truncated_json(text)
        assert result == {"a": 1}

    def test_missing_closing_brace(self):
        result = self.client._recover_truncated_json('{"a": 1')
        assert result == {"a": 1}

    def test_deeply_nested_truncated(self):
        result = self.client._recover_truncated_json('{"a": {"b": {"c": 3')
        assert result["a"]["b"]["c"] == 3

    def test_invalid_cannot_recover(self):
        # Completely malformed (not even valid JSON start)
        result = self.client._recover_truncated_json("not json at all {{{{")
        assert result is None

    def test_nested_strings_with_braces_not_counted(self):
        # Braces inside strings should not be counted as structural
        text = '{"template": "use {placeholder} here"'
        result = self.client._recover_truncated_json(text)
        assert result is not None
        assert "template" in result


# ============================================================================
# LLMClient.call — primary / fallback model routing (mocked)
# ============================================================================

class TestLLMClientCall:
    def setup_method(self):
        _reset_circuits()

    def teardown_method(self):
        _reset_circuits()

    def _make_api_response(self, text: str):
        resp = MagicMock()
        resp.content = [MagicMock(text=text)]
        resp.usage.input_tokens = 10
        resp.usage.output_tokens = 5
        return resp

    def test_primary_model_used_when_circuit_closed(self):
        client = _make_client()
        api_resp = self._make_api_response('{"result": "ok"}')
        client._client.messages.create.return_value = api_resp

        result = client.call(system="sys", messages=[{"role": "user", "content": "hi"}])
        assert result.model_used == PRIMARY_MODEL
        assert result.used_fallback is False

    def test_fallback_model_used_when_primary_circuit_open(self):
        client = _make_client()
        # Open the primary circuit by recording enough failures
        _reset_circuits()
        for _ in range(CIRCUIT_OPEN_THRESHOLD):
            lc._circuits[PRIMARY_MODEL].record_failure()
        assert lc._circuits[PRIMARY_MODEL].is_open

        api_resp = self._make_api_response('{"result": "fallback"}')
        client._client.messages.create.return_value = api_resp

        result = client.call(system="sys", messages=[{"role": "user", "content": "hi"}])
        assert result.model_used == FALLBACK_MODEL
        assert result.used_fallback is True

    def test_both_circuits_open_raises_runtime_error(self):
        _reset_circuits()
        for _ in range(CIRCUIT_OPEN_THRESHOLD):
            lc._circuits[PRIMARY_MODEL].record_failure()
            lc._circuits[FALLBACK_MODEL].record_failure()

        client = _make_client()
        with pytest.raises(RuntimeError, match="circuit-broken"):
            client.call(system="sys", messages=[{"role": "user", "content": "hi"}])

    def test_success_resets_circuit(self):
        client = _make_client()
        _reset_circuits()
        # Record some failures (below threshold)
        lc._circuits[PRIMARY_MODEL].failures = 2
        api_resp = self._make_api_response('{"ok": true}')
        client._client.messages.create.return_value = api_resp

        client.call(system="sys", messages=[{"role": "user", "content": "hi"}])
        assert lc._circuits[PRIMARY_MODEL].failures == 0


# ============================================================================
# CircuitState
# ============================================================================

class TestCircuitState:
    def test_initially_closed(self):
        state = CircuitState()
        assert state.is_open is False

    def test_opens_after_threshold(self):
        state = CircuitState()
        for _ in range(CIRCUIT_OPEN_THRESHOLD):
            state.record_failure()
        assert state.is_open is True

    def test_below_threshold_stays_closed(self):
        state = CircuitState()
        for _ in range(CIRCUIT_OPEN_THRESHOLD - 1):
            state.record_failure()
        assert state.is_open is False

    def test_success_resets(self):
        state = CircuitState()
        for _ in range(CIRCUIT_OPEN_THRESHOLD):
            state.record_failure()
        state.record_success()
        assert state.is_open is False
        assert state.failures == 0

    def test_auto_reset_after_cooldown(self):
        state = CircuitState()
        for _ in range(CIRCUIT_OPEN_THRESHOLD):
            state.record_failure()

        # Backdate opened_at so reset window has passed
        from datetime import timezone, timedelta, datetime
        state.opened_at = datetime.now(timezone.utc) - timedelta(seconds=lc.CIRCUIT_RESET_SECONDS + 1)
        assert state.is_open is False  # Should auto-reset


# ============================================================================
# Retry with exponential backoff (mocked time.sleep)
# ============================================================================

class TestRetryLogic:
    def setup_method(self):
        _reset_circuits()

    def teardown_method(self):
        _reset_circuits()

    @patch("llm_client.time.sleep")
    def test_retries_on_server_error(self, mock_sleep):
        import anthropic
        client = _make_client()

        err_resp = MagicMock()
        err_resp.status_code = 500

        api_ok = MagicMock()
        api_ok.content = [MagicMock(text='{"ok": true}')]
        api_ok.usage.input_tokens = 5
        api_ok.usage.output_tokens = 5

        # Fail once, then succeed
        client._client.messages.create.side_effect = [
            anthropic.APIStatusError("Server error", response=err_resp, body={}),
            api_ok,
        ]

        result = client._call_with_retry(
            PRIMARY_MODEL,
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=100,
            temperature=0.3,
        )
        assert result.content == '{"ok": true}'
        mock_sleep.assert_called_once()

    @patch("llm_client.time.sleep")
    def test_quota_error_waits_longer(self, mock_sleep):
        import anthropic
        client = _make_client()

        err_resp = MagicMock()
        err_resp.status_code = 429

        api_ok = MagicMock()
        api_ok.content = [MagicMock(text='{"ok": true}')]
        api_ok.usage.input_tokens = 5
        api_ok.usage.output_tokens = 5

        quota_exc = anthropic.RateLimitError("quota exceeded daily limit", response=err_resp, body={})
        client._client.messages.create.side_effect = [quota_exc, api_ok]

        client._call_with_retry(
            PRIMARY_MODEL,
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=100,
            temperature=0.3,
        )
        # quota wait should be QUOTA_WAIT_SECONDS, not BACKOFF_BASE^0 = 1
        sleep_call_args = mock_sleep.call_args_list
        assert len(sleep_call_args) == 1
        waited = sleep_call_args[0][0][0]
        assert waited == QUOTA_WAIT_SECONDS

    @patch("llm_client.time.sleep")
    def test_all_retries_exhausted_raises(self, mock_sleep):
        import anthropic
        client = _make_client()

        err_resp = MagicMock()
        err_resp.status_code = 500

        client._client.messages.create.side_effect = anthropic.APIStatusError(
            "Persistent error", response=err_resp, body={}
        )

        with pytest.raises(RuntimeError, match="All .* attempts failed"):
            client._call_with_retry(
                PRIMARY_MODEL,
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=100,
                temperature=0.3,
            )

    @patch("llm_client.time.sleep")
    def test_4xx_not_retried(self, mock_sleep):
        import anthropic
        client = _make_client()

        err_resp = MagicMock()
        err_resp.status_code = 400

        client._client.messages.create.side_effect = anthropic.APIStatusError(
            "Bad request", response=err_resp, body={}
        )

        with pytest.raises(anthropic.APIStatusError):
            client._call_with_retry(
                PRIMARY_MODEL,
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=100,
                temperature=0.3,
            )
        # 4xx should NOT trigger sleep (no retry)
        mock_sleep.assert_not_called()
