"""Usage data providers for the Sense HAT display.

Two sources share a common ``get_usage() -> Usage`` interface:

* ``LiveDataSource`` wraps the existing ``ClaudeAPIClient`` and maps the Claude.ai
  API response (and any errors) into a small ``Usage`` value.
* ``DemoDataSource`` produces a synthetic 0->100 sweep so the LED rendering can be
  built and tuned on the emulator without credentials or network access.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Feed states. "ok" means five_hour/seven_day are meaningful; everything else is a
# non-data condition the display should signal instead of showing stale values.
STATE_OK = "ok"
STATE_LOADING = "loading"
STATE_AUTH = "auth_expired"
STATE_RATE_LIMITED = "rate_limited"
STATE_NETWORK = "network_error"
STATE_ERROR = "error"

# Nominal length of the rolling 5-hour limit window, used to turn a single
# ``resets_at`` timestamp into a "fraction of the window still remaining".
FIVE_HOUR_WINDOW_SECONDS = 5 * 3600


@dataclass
class Usage:
    """A single usage snapshot the display knows how to render."""

    five_hour: float = 0.0
    seven_day: float = 0.0
    state: str = STATE_LOADING
    # ISO 8601 reset timestamps (or None) so the display can count down the time
    # left in each window, not just show its utilization.
    five_hour_resets_at: str | None = None
    seven_day_resets_at: str | None = None

    @property
    def worst(self) -> float:
        """The more-critical of the two windows (mirrors the tray icon's max())."""
        return max(self.five_hour, self.seven_day)


def seconds_until(iso_timestamp: str | None) -> float | None:
    """Seconds from now until an ISO 8601 timestamp.

    Returns ``None`` if the timestamp is missing or unparseable, and a negative
    value if the moment has already passed (callers decide how to clamp).
    """
    if not iso_timestamp:
        return None
    try:
        reset = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return (reset - datetime.now(timezone.utc)).total_seconds()


def _pct(block) -> float:
    """Safely pull a utilization percentage out of an API sub-object.

    The API returns either a ``{"utilization": <num>}`` dict or ``None`` for a
    window, so guard both shapes and clamp into 0..100.
    """
    if isinstance(block, dict):
        value = block.get("utilization")
        if value is not None:
            try:
                return max(0.0, min(100.0, float(value)))
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _resets_at(block) -> str | None:
    """Pull the ``resets_at`` ISO string out of an API sub-object, if present."""
    if isinstance(block, dict):
        return block.get("resets_at")
    return None


def usage_from_api(data: dict) -> Usage:
    """Map a raw Claude.ai usage payload into a ``Usage``."""
    return Usage(
        five_hour=_pct(data.get("five_hour")),
        seven_day=_pct(data.get("seven_day")),
        state=STATE_OK,
        five_hour_resets_at=_resets_at(data.get("five_hour")),
        seven_day_resets_at=_resets_at(data.get("seven_day")),
    )


class LiveDataSource:
    """Fetches real usage via the existing ``ClaudeAPIClient``."""

    def __init__(self, org_id: str, session_cookie: str, device_id: str):
        # Imported lazily so --demo works without `requests` installed and so the
        # error/exception types come from the one canonical definition in src/.
        from src.api_client import (
            AuthenticationError,
            ClaudeAPIClient,
            ClaudeAPIError,
            NetworkError,
            RateLimitError,
        )

        self._AuthenticationError = AuthenticationError
        self._RateLimitError = RateLimitError
        self._NetworkError = NetworkError
        self._ClaudeAPIError = ClaudeAPIError
        self.client = ClaudeAPIClient(org_id, session_cookie, device_id)

    def get_usage(self) -> Usage:
        try:
            data = self.client.get_usage()
            usage = usage_from_api(data)
            logger.debug(f"Live usage: 5h={usage.five_hour} 7d={usage.seven_day}")
            return usage
        except self._AuthenticationError:
            logger.error("Authentication failed - session cookie expired")
            return Usage(state=STATE_AUTH)
        except self._RateLimitError as e:
            logger.warning(f"Rate limited, retry after {e.retry_after}s")
            return Usage(state=STATE_RATE_LIMITED)
        except self._NetworkError as e:
            logger.warning(f"Network error: {e}")
            return Usage(state=STATE_NETWORK)
        except self._ClaudeAPIError as e:
            logger.error(f"API error: {e}")
            return Usage(state=STATE_ERROR)


class DemoDataSource:
    """Synthetic data for emulator development - no credentials needed.

    Each ``get_usage()`` call advances a triangle wave so the bars visibly sweep
    0->100->0. The two windows are phase-shifted so they don't move in lockstep,
    which makes the dual-bar layout easy to read while tuning.
    """

    def __init__(self, step: float = 4.0):
        self.step = step
        self._t = 0.0

    @staticmethod
    def _triangle(phase: float) -> float:
        """Map a 0..200 phase onto a 0->100->0 triangle wave."""
        phase %= 200.0
        return phase if phase <= 100.0 else 200.0 - phase

    def get_usage(self) -> Usage:
        from datetime import timedelta

        self._t = (self._t + self.step) % 200.0
        five = self._triangle(self._t)
        seven = self._triangle(self._t + 60.0)  # phase-shifted second window

        # Synthesize reset timestamps so the countdown bar visibly drains: the
        # 5-hour window's remaining time sweeps full -> empty across the cycle.
        now = datetime.now(timezone.utc)
        remaining = (200.0 - self._t) / 200.0  # 1.0 -> 0.0 over a full cycle
        five_reset = now + timedelta(seconds=remaining * FIVE_HOUR_WINDOW_SECONDS)
        seven_reset = now + timedelta(days=3, hours=4)
        return Usage(
            five_hour=five,
            seven_day=seven,
            state=STATE_OK,
            five_hour_resets_at=five_reset.isoformat(),
            seven_day_resets_at=seven_reset.isoformat(),
        )
