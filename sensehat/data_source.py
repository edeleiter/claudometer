"""Usage data providers for the Sense HAT display.

Two sources share a common ``get_usage() -> Usage`` interface:

* ``LiveDataSource`` wraps the existing ``ClaudeAPIClient`` and maps the Claude.ai
  API response (and any errors) into a small ``Usage`` value.
* ``DemoDataSource`` produces a synthetic 0->100 sweep so the LED rendering can be
  built and tuned on the emulator without credentials or network access.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Feed states. "ok" means five_hour/seven_day are meaningful; everything else is a
# non-data condition the display should signal instead of showing stale values.
STATE_OK = "ok"
STATE_LOADING = "loading"
STATE_AUTH = "auth_expired"
STATE_RATE_LIMITED = "rate_limited"
STATE_NETWORK = "network_error"
STATE_ERROR = "error"


@dataclass
class Usage:
    """A single usage snapshot the display knows how to render."""

    five_hour: float = 0.0
    seven_day: float = 0.0
    state: str = STATE_LOADING

    @property
    def worst(self) -> float:
        """The more-critical of the two windows (mirrors the tray icon's max())."""
        return max(self.five_hour, self.seven_day)


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


def usage_from_api(data: dict) -> Usage:
    """Map a raw Claude.ai usage payload into a ``Usage``."""
    return Usage(
        five_hour=_pct(data.get("five_hour")),
        seven_day=_pct(data.get("seven_day")),
        state=STATE_OK,
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
        self._t = (self._t + self.step) % 200.0
        five = self._triangle(self._t)
        seven = self._triangle(self._t + 60.0)  # phase-shifted second window
        return Usage(five_hour=five, seven_day=seven, state=STATE_OK)
