"""
LLM Client for Universal Agent Team.

Provides Claude API access with:
- Primary model:  claude-opus-4-6
- Fallback model: claude-sonnet-4-6
- Automatic retry with exponential backoff (TRANSIENT errors)
- Circuit breaker (stop hammering a broken endpoint)
- Structured JSON output extraction
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import anthropic


# ============================================================================
# Constants
# ============================================================================

PRIMARY_MODEL   = "claude-opus-4-6"
FALLBACK_MODEL  = "claude-sonnet-4-6"

MAX_TOKENS_DEFAULT = 8192
TEMPERATURE_DEFAULT = 0.3
TIMEOUT_SECONDS = 300

MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds  (2^attempt)

# When a quota / daily-limit 429 is detected, wait this long before retrying
QUOTA_WAIT_SECONDS = 60

# Circuit breaker: open after N consecutive failures, reset after M seconds
CIRCUIT_OPEN_THRESHOLD = 3
CIRCUIT_RESET_SECONDS  = 60


# ============================================================================
# Circuit Breaker (per-model)
# ============================================================================

@dataclass
class CircuitState:
    """Per-model circuit breaker state."""
    failures: int = 0
    opened_at: Optional[datetime] = None

    @property
    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self.opened_at).total_seconds()
        if elapsed >= CIRCUIT_RESET_SECONDS:
            # Auto-reset after cooldown
            self.failures = 0
            self.opened_at = None
            return False
        return True

    def record_failure(self):
        self.failures += 1
        if self.failures >= CIRCUIT_OPEN_THRESHOLD:
            self.opened_at = datetime.now(timezone.utc)

    def record_success(self):
        self.failures = 0
        self.opened_at = None


_circuits: Dict[str, CircuitState] = {
    PRIMARY_MODEL:  CircuitState(),
    FALLBACK_MODEL: CircuitState(),
}


# ============================================================================
# LLM Response
# ============================================================================

@dataclass
class LLMResponse:
    """Result of an LLM call."""
    content: str
    model_used: str
    input_tokens: int
    output_tokens: int
    used_fallback: bool = False


# ============================================================================
# LLM Client
# ============================================================================

class LLMClient:
    """
    Thread-safe Claude API client with automatic fallback.

    Usage::

        client = LLMClient()
        response = client.call(
            system="You are a planning agent.",
            messages=[{"role": "user", "content": "Build a todo app"}],
        )
        print(response.content)
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Support both ANTHROPIC_API_KEY (standard) and ANTHROPIC_AUTH_TOKEN (enterprise/proxy)
        self.api_key = (
            api_key
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or self._load_from_claude_settings("ANTHROPIC_AUTH_TOKEN")
            or ""
        )
        self.base_url = (
            base_url
            or os.environ.get("ANTHROPIC_BASE_URL")
            or self._load_from_claude_settings("ANTHROPIC_BASE_URL")
        )

        client_kwargs: Dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self._client = anthropic.Anthropic(**client_kwargs)
        self.logger = logging.getLogger("llm_client")

    @staticmethod
    def _load_from_claude_settings(key: str) -> Optional[str]:
        """Load a value from /root/.claude/settings.json if it exists."""
        try:
            import json as _json
            settings_path = os.path.expanduser("~/.claude/settings.json")
            with open(settings_path) as f:
                data = _json.load(f)
            return data.get("env", {}).get(key)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def call(
        self,
        system: str,
        messages: List[Dict[str, str]],
        max_tokens: int = MAX_TOKENS_DEFAULT,
        temperature: float = TEMPERATURE_DEFAULT,
    ) -> LLMResponse:
        """
        Call the LLM with automatic retry and model fallback.

        Attempt order:
          1. PRIMARY_MODEL (claude-opus-4-6)
          2. FALLBACK_MODEL (claude-sonnet-4-6)   ← if primary circuit is open

        Args:
            system: System prompt
            messages: Conversation messages list
            max_tokens: Max output tokens
            temperature: Sampling temperature

        Returns:
            LLMResponse with content and usage stats

        Raises:
            RuntimeError: If both models fail after all retries
        """
        # Try primary model first (unless circuit is open)
        if not _circuits[PRIMARY_MODEL].is_open:
            try:
                resp = self._call_with_retry(
                    PRIMARY_MODEL, system, messages, max_tokens, temperature
                )
                _circuits[PRIMARY_MODEL].record_success()
                return resp
            except Exception as exc:
                self.logger.warning(
                    f"Primary model {PRIMARY_MODEL} failed: {exc}. "
                    f"Switching to fallback {FALLBACK_MODEL}."
                )
                _circuits[PRIMARY_MODEL].record_failure()
        else:
            self.logger.warning(
                f"Circuit OPEN for {PRIMARY_MODEL}, using {FALLBACK_MODEL} directly."
            )

        # Fallback model
        if _circuits[FALLBACK_MODEL].is_open:
            raise RuntimeError(
                f"Both models are circuit-broken. "
                f"Primary: {PRIMARY_MODEL}, Fallback: {FALLBACK_MODEL}"
            )

        try:
            resp = self._call_with_retry(
                FALLBACK_MODEL, system, messages, max_tokens, temperature
            )
            _circuits[FALLBACK_MODEL].record_success()
            resp.used_fallback = True
            return resp
        except Exception as exc:
            _circuits[FALLBACK_MODEL].record_failure()
            raise RuntimeError(
                f"Both models failed. Last error: {exc}"
            ) from exc

    def extract_json(self, response: LLMResponse) -> Dict[str, Any]:
        """
        Extract the first JSON object / array from LLM response text.

        Handles these output patterns robustly:
          1. ```json ... ``` fenced block (possibly truncated)
          2. Bare JSON object starting with {
          3. JSON embedded anywhere in prose
          4. Truncated JSON (attempts bracket-completion recovery)
        """
        text = response.content.strip()

        # Pattern 1: fenced code block (handle missing closing ```)
        if "```json" in text:
            start = text.index("```json") + len("```json")
            end   = text.find("```", start)
            text  = text[start:end].strip() if end != -1 else text[start:].strip()
        elif "```" in text:
            start = text.index("```") + 3
            # skip language tag if present
            nl = text.find("\n", start)
            if nl != -1 and nl - start < 20:
                start = nl + 1
            end  = text.find("```", start)
            text = text[start:end].strip() if end != -1 else text[start:].strip()

        # Pattern 2: locate first { or [
        for char in ("{", "["):
            idx = text.find(char)
            if idx != -1:
                text = text[idx:]
                break

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Recovery: try to close truncated JSON by appending missing brackets
        recovered = self._recover_truncated_json(text)
        if recovered is not None:
            self.logger.warning("Recovered truncated JSON response")
            return recovered

        self.logger.error(f"JSON parse failed. Raw content:\n{response.content[:600]}")
        raise ValueError(f"LLM response is not valid JSON (even after recovery attempt)")

    def _recover_truncated_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Try to recover a truncated JSON string by closing open brackets/braces.
        Returns parsed dict on success, None on failure.
        """
        # Count open braces/brackets to figure out what's missing
        stack = []
        in_string = False
        escape_next = False

        for ch in text:
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in ("{", "["):
                stack.append("}" if ch == "{" else "]")
            elif ch in ("}", "]") and stack:
                stack.pop()

        # Close unclosed string if needed
        if in_string:
            text += '"'

        # Append closing brackets in reverse order
        closing = "".join(reversed(stack))
        candidate = text + closing

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_with_retry(
        self,
        model: str,
        system: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Retry up to MAX_RETRIES times with exponential backoff."""
        last_exc: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                self.logger.debug(
                    f"[{model}] Attempt {attempt + 1}/{MAX_RETRIES}"
                )
                result = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                )
                return LLMResponse(
                    content=result.content[0].text,
                    model_used=model,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                )
            except anthropic.RateLimitError as exc:
                # Distinguish quota exhaustion (daily/monthly limit) from
                # transient rate limits.  Quota errors need a longer wait so
                # the window can reset; transient 429s use exponential backoff.
                exc_str = str(exc).lower()
                is_quota = any(
                    kw in exc_str
                    for kw in ("quota", "exceeded", "daily", "monthly", "insufficient_quota")
                )
                wait = QUOTA_WAIT_SECONDS if is_quota else BACKOFF_BASE ** attempt
                self.logger.warning(
                    f"[{model}] {'Quota exhausted' if is_quota else 'Rate limit'}. "
                    f"Waiting {wait}s (attempt {attempt+1})"
                )
                time.sleep(wait)
                last_exc = exc
            except anthropic.APIStatusError as exc:
                if exc.status_code >= 500:
                    wait = BACKOFF_BASE ** attempt
                    self.logger.warning(
                        f"[{model}] Server error {exc.status_code}. "
                        f"Waiting {wait}s (attempt {attempt+1})"
                    )
                    time.sleep(wait)
                    last_exc = exc
                else:
                    raise  # 4xx errors are not retriable
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = BACKOFF_BASE ** attempt
                    self.logger.warning(
                        f"[{model}] Unexpected error: {exc}. "
                        f"Waiting {wait}s (attempt {attempt+1})"
                    )
                    time.sleep(wait)

        raise RuntimeError(
            f"[{model}] All {MAX_RETRIES} attempts failed. "
            f"Last error: {last_exc}"
        ) from last_exc


# ============================================================================
# Module-level singleton (lazy init)
# ============================================================================

_default_client: Optional[LLMClient] = None


def get_client() -> LLMClient:
    """Return the shared LLMClient instance."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
