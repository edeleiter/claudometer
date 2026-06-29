"""Rendering of usage onto the 8x8 Sense HAT LED matrix.

``SenseHatDisplay`` owns the SenseHat handle and translates a ``Usage`` snapshot
into pixels. It offers three usage modes (cycled by the joystick) plus distinct
glyphs for non-data states. Colors and the tier thresholds are ported from the
Windows tray app's ``IconGenerator`` so the two stay visually consistent.
"""

import logging

from .data_source import (
    STATE_AUTH,
    STATE_LOADING,
    STATE_NETWORK,
    STATE_OK,
    STATE_RATE_LIMITED,
    Usage,
)

logger = logging.getLogger(__name__)

OFF = (0, 0, 0)

# Tier palette (RGB), matching IconGenerator.COLORS in src/icon_generator.py.
GREEN = (0, 200, 60)  # 0-49%
YELLOW = (255, 193, 7)  # 50-74%
ORANGE = (255, 120, 0)  # 75-89%
RED = (244, 40, 40)  # 90-100%
GRAY = (120, 120, 120)  # error / disconnected
BLUE = (33, 150, 243)  # auth required
WHITE = (220, 220, 220)
BASELINE = (50, 50, 60)  # dim "zero line" so a 0% bar is still visibly alive

# Display modes (cycled left/right on the joystick).
MODE_DUAL = 0  # two bars: 5-hour vs 7-day
MODE_METER = 1  # single bar of the worse window
MODE_SCROLL = 2  # scroll the exact numbers
MODES = (MODE_DUAL, MODE_METER, MODE_SCROLL)
MODE_NAMES = {MODE_DUAL: "dual-bars", MODE_METER: "meter", MODE_SCROLL: "scroll"}

# Dual-bar layout: two 3-wide bars with a 2-column gap down the middle.
LEFT_COLS = (0, 1, 2)
RIGHT_COLS = (5, 6, 7)

# 8x8 glyphs for non-data states ('#' = lit). Kept tiny and static so the joystick
# stays responsive (unlike the blocking show_message scroller).
_GLYPHS = {
    "!": [
        "...##...",
        "...##...",
        "...##...",
        "...##...",
        "...##...",
        "........",
        "...##...",
        "........",
    ],
    "?": [
        "..####..",
        ".#....#.",
        "......#.",
        ".....#..",
        "....#...",
        "...#....",
        "........",
        "...#....",
    ],
    "X": [
        "#......#",
        ".#....#.",
        "..#..#..",
        "...##...",
        "...##...",
        "..#..#..",
        ".#....#.",
        "#......#",
    ],
}


def tier_color(pct: float):
    """Map a usage percentage to its tier color (green/yellow/orange/red)."""
    if pct < 50:
        return GREEN
    elif pct < 75:
        return YELLOW
    elif pct < 90:
        return ORANGE
    return RED


def _rows_for(pct: float) -> int:
    """How many of the 8 rows to light for a percentage.

    Any non-zero usage lights at least the bottom row so a small-but-present
    value is never invisible.
    """
    if pct <= 0:
        return 0
    return max(1, min(8, round(pct / 100.0 * 8)))


class SenseHatDisplay:
    """Draws Usage onto the Sense HAT matrix."""

    def __init__(self, sense, rotation: int = 0, low_light: bool = True,
                 scroll_speed: float = 0.08):
        self.sense = sense
        self.scroll_speed = scroll_speed
        try:
            self.sense.set_rotation(rotation)
        except Exception as e:
            logger.debug(f"set_rotation failed: {e}")
        self.set_low_light(low_light)

    # -- public API ---------------------------------------------------------

    def set_low_light(self, enabled: bool) -> None:
        """Toggle the Sense HAT's dimmed-LED mode."""
        self.low_light = enabled
        try:
            self.sense.low_light = enabled
        except Exception as e:
            logger.debug(f"low_light toggle failed: {e}")

    def show_usage(self, usage: Usage, mode: int, tick: int = 0) -> bool:
        """Render a snapshot in the given mode.

        Returns True if it performed a blocking scroll (the caller should then
        re-read state and loop), False for a fast static frame.
        """
        if usage.state != STATE_OK:
            self._show_state(usage.state, tick)
            return False

        if mode == MODE_METER:
            self._meter(usage)
            return False
        if mode == MODE_SCROLL:
            self._scroll(usage)
            return True
        # Default / MODE_DUAL
        self._dual_bars(usage)
        return False

    def clear(self) -> None:
        try:
            self.sense.clear()
        except Exception as e:
            logger.debug(f"clear failed: {e}")

    # -- usage modes --------------------------------------------------------

    def _dual_bars(self, usage: Usage) -> None:
        grid = self._blank()
        self._fill_bar(grid, LEFT_COLS, usage.five_hour)
        self._fill_bar(grid, RIGHT_COLS, usage.seven_day)
        self._push(grid)

    def _meter(self, usage: Usage) -> None:
        grid = self._blank()
        self._fill_bar(grid, range(8), usage.worst)
        self._push(grid)

    def _scroll(self, usage: Usage) -> None:
        text = f"5h {int(round(usage.five_hour))} 7d {int(round(usage.seven_day))}"
        color = tier_color(usage.worst)
        try:
            self.sense.show_message(text, text_colour=list(color),
                                    scroll_speed=self.scroll_speed)
        except Exception as e:
            logger.debug(f"show_message failed: {e}")
        finally:
            self.clear()

    # -- non-data states ----------------------------------------------------

    def _show_state(self, state: str, tick: int) -> None:
        if state == STATE_AUTH:
            self._draw_glyph("!", BLUE)
        elif state == STATE_NETWORK:
            self._draw_glyph("?", GRAY)
        elif state == STATE_RATE_LIMITED:
            self._draw_glyph("?", ORANGE)
        elif state == STATE_LOADING:
            self._loading(tick)
        else:  # STATE_ERROR / unknown
            self._draw_glyph("X", GRAY)

    def _loading(self, tick: int) -> None:
        """A single dim pixel walking around the border edge."""
        border = [(x, 0) for x in range(8)] + [(7, y) for y in range(1, 8)] + \
                 [(x, 7) for x in range(6, -1, -1)] + [(0, y) for y in range(6, 0, -1)]
        grid = self._blank()
        x, y = border[tick % len(border)]
        grid[y * 8 + x] = (90, 90, 130)
        self._push(grid)

    # -- low-level helpers --------------------------------------------------

    @staticmethod
    def _blank() -> list:
        return [OFF] * 64

    @staticmethod
    def _fill_bar(grid: list, cols, pct: float) -> None:
        """Light the bottom ``_rows_for(pct)`` rows of ``cols`` in the tier color.

        A dim baseline is always drawn on the bottom row so a 0% bar still shows
        (and the bar's columns are identifiable) instead of going fully dark.
        """
        for x in cols:
            grid[7 * 8 + x] = BASELINE
        rows = _rows_for(pct)
        if rows <= 0:
            return
        color = tier_color(pct)
        for y in range(8 - rows, 8):
            for x in cols:
                grid[y * 8 + x] = color

    def _draw_glyph(self, symbol: str, color) -> None:
        pattern = _GLYPHS[symbol]
        grid = self._blank()
        for y, row in enumerate(pattern):
            for x, ch in enumerate(row):
                if ch != "." and ch != " ":
                    grid[y * 8 + x] = color
        self._push(grid)

    def _push(self, grid: list) -> None:
        try:
            self.sense.set_pixels(grid)
        except Exception as e:
            logger.debug(f"set_pixels failed: {e}")
