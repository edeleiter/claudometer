"""Tests for the Sense HAT reset-countdown rendering and data plumbing.

These cover the pieces that are pure/host-testable (no LED hardware): the
ISO-timestamp math, the API->Usage mapping of ``resets_at``, and that the
dual-bars screen paints a timer bar in the right-hand columns.
"""

from datetime import datetime, timedelta, timezone

from sensehat.data_source import (
    FIVE_HOUR_WINDOW_SECONDS,
    STATE_OK,
    Usage,
    seconds_until,
    usage_from_api,
)
from sensehat.display import (
    LEFT_COLS,
    RIGHT_COLS,
    TIMER,
    SenseHatDisplay,
    _fraction_remaining,
    tier_color,
)


def _iso_in(**delta) -> str:
    return (datetime.now(timezone.utc) + timedelta(**delta)).isoformat()


class FakeSense:
    """Minimal Sense HAT stand-in that records the last pushed grid."""

    low_light = False

    def __init__(self):
        self.pixels = None

    def set_rotation(self, *a, **k):
        pass

    def set_pixels(self, grid):
        self.pixels = list(grid)

    def clear(self):
        self.pixels = [(0, 0, 0)] * 64


# -- seconds_until ----------------------------------------------------------


def test_seconds_until_future_is_positive():
    secs = seconds_until(_iso_in(hours=2))
    assert secs is not None and 7100 < secs < 7300  # ~2h with test slack


def test_seconds_until_handles_none_and_garbage():
    assert seconds_until(None) is None
    assert seconds_until("not-a-timestamp") is None


def test_seconds_until_past_is_negative():
    assert seconds_until(_iso_in(hours=-1)) < 0


# -- _fraction_remaining ----------------------------------------------------


def test_fraction_full_window_is_near_one():
    frac = _fraction_remaining(_iso_in(seconds=FIVE_HOUR_WINDOW_SECONDS), FIVE_HOUR_WINDOW_SECONDS)
    assert 0.98 <= frac <= 1.0


def test_fraction_half_window():
    frac = _fraction_remaining(_iso_in(seconds=FIVE_HOUR_WINDOW_SECONDS / 2), FIVE_HOUR_WINDOW_SECONDS)
    assert 0.45 < frac < 0.55


def test_fraction_past_reset_is_zero_and_unknown_is_none():
    assert _fraction_remaining(_iso_in(hours=-1), FIVE_HOUR_WINDOW_SECONDS) == 0.0
    assert _fraction_remaining(None, FIVE_HOUR_WINDOW_SECONDS) is None


# -- usage_from_api captures resets_at --------------------------------------


def test_usage_from_api_keeps_reset_timestamps():
    five_reset = _iso_in(hours=2)
    seven_reset = _iso_in(days=3)
    usage = usage_from_api({
        "five_hour": {"utilization": 45, "resets_at": five_reset},
        "seven_day": {"utilization": 30, "resets_at": seven_reset},
    })
    assert usage.five_hour == 45
    assert usage.five_hour_resets_at == five_reset
    assert usage.seven_day_resets_at == seven_reset


# -- dual-bars renders a timer in the right columns -------------------------


def test_dual_bars_left_is_usage_right_is_timer():
    sense = FakeSense()
    display = SenseHatDisplay(sense)
    usage = Usage(
        five_hour=50.0,
        seven_day=99.0,  # must NOT appear: right bar is now the 5h countdown
        state=STATE_OK,
        five_hour_resets_at=_iso_in(seconds=FIVE_HOUR_WINDOW_SECONDS),  # ~full
    )
    display._dual_bars(usage)
    grid = sense.pixels

    # Left columns carry the 5-hour utilization tier color (50% -> yellow band).
    left_colors = {grid[y * 8 + x] for y in range(8) for x in LEFT_COLS}
    assert tier_color(50.0) in left_colors

    # Right columns carry the TIMER color, never the 7-day (red) tier color.
    right_colors = {grid[y * 8 + x] for y in range(8) for x in RIGHT_COLS}
    assert TIMER in right_colors
    assert tier_color(99.0) not in right_colors
