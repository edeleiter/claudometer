"""Import shim that returns a SenseHat from real hardware, the emulator, or a stub.

The ``sense_hat`` (real Pi) and ``sense_emu`` (desktop emulator) packages expose
an identically-shaped ``SenseHat`` class, so the rest of the app can stay
hardware-agnostic and just consume whatever this factory returns.

A third "stub" backend renders the matrix as ASCII to the terminal. It needs no
GUI or hardware, which makes it handy for headless smoke tests and CI.

Backend selection (highest priority first):
1. ``backend`` argument / ``CLAUDOMETER_BACKEND`` env in {hardware, emulator, stub, auto}.
2. ``CLAUDOMETER_EMULATOR=1`` (or ``force_emulator=True``) -> emulator.
3. auto: try ``sense_hat`` (the Pi), then ``sense_emu``.
"""

import logging
import os

logger = logging.getLogger(__name__)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def use_emulator(force_emulator: bool = False) -> bool:
    """Decide whether the emulator backend should be used."""
    return force_emulator or _truthy(os.environ.get("CLAUDOMETER_EMULATOR"))


def get_sense(force_emulator: bool = False, backend: str | None = None):
    """Return a ready-to-use SenseHat-like instance.

    Args:
        force_emulator: When True, prefer the emulator regardless of env.
        backend: Explicit backend ("hardware", "emulator", "stub", "auto"); falls
            back to the ``CLAUDOMETER_BACKEND`` env var, else "auto".

    Returns:
        A tuple ``(sense, backend_name)``.

    Raises:
        RuntimeError: If the requested backend cannot be provided.
    """
    choice = (backend or os.environ.get("CLAUDOMETER_BACKEND") or "auto").lower()

    if choice == "stub":
        logger.info("Using stub (ASCII) backend")
        return StubSenseHat(), "stub"

    if choice == "hardware":
        sense = _import_hardware()
        if sense is not None:
            return sense, "hardware"
        raise RuntimeError("Sense HAT hardware backend requested but unavailable.")

    if choice == "emulator" or use_emulator(force_emulator):
        sense = _import_emulator()
        if sense is not None:
            logger.info("Using Sense HAT emulator backend")
            return sense, "emulator"
        raise RuntimeError(
            "Emulator requested but 'sense_emu' is not installed. "
            "Install it with: pip install sense-emu"
        )

    # auto: prefer real hardware, fall back to the emulator for desktop dev.
    sense = _import_hardware()
    if sense is not None:
        logger.info("Using Sense HAT hardware backend")
        return sense, "hardware"

    sense = _import_emulator()
    if sense is not None:
        logger.info("Sense HAT hardware unavailable; using emulator backend")
        return sense, "emulator"

    raise RuntimeError(
        "No Sense HAT backend available. Install 'sense-hat' on the Raspberry Pi "
        "(sudo apt install sense-hat), 'sense-emu' on a desktop "
        "(pip install sense-emu), or pass --backend stub for an ASCII preview."
    )


def _import_hardware():
    try:
        from sense_hat import SenseHat  # type: ignore
    except Exception as e:  # ImportError, plus OSError when no HAT is attached
        logger.debug(f"sense_hat unavailable: {e}")
        return None
    try:
        return SenseHat()
    except Exception as e:
        logger.debug(f"sense_hat present but failed to initialize: {e}")
        return None


def _import_emulator():
    try:
        from sense_emu import SenseHat  # type: ignore
    except Exception as e:
        logger.debug(f"sense_emu unavailable: {e}")
        return None
    try:
        return SenseHat()
    except Exception as e:
        logger.debug(f"sense_emu present but failed to initialize: {e}")
        return None


class _StubStick:
    """Joystick stand-in for the stub backend (never emits events)."""

    def get_events(self):
        return []

    @property
    def direction_any(self):
        return None

    @direction_any.setter
    def direction_any(self, _callback):
        pass


class StubSenseHat:
    """A headless SenseHat that prints the matrix as ASCII art.

    Implements just the surface the display/app use (``set_pixels``, ``clear``,
    ``set_rotation``, ``low_light``, ``show_message``, ``stick``) so the full
    render path can be exercised with no GUI or hardware.
    """

    def __init__(self):
        self.low_light = False
        self._rotation = 0
        self.stick = _StubStick()

    def set_rotation(self, rotation):
        self._rotation = rotation

    def clear(self, *_args):
        # Blank frame (keeps terminal output stable between renders).
        self.set_pixels([(0, 0, 0)] * 64)

    def set_pixel(self, x, y, *color):
        pass  # not used by the display (it batches via set_pixels)

    def show_message(self, text, **_kwargs):
        print(f"[scroll] {text}")

    def set_pixels(self, pixels):
        # 24-bit ANSI color blocks; falls back gracefully if the terminal ignores them.
        lines = []
        for y in range(8):
            cells = []
            for x in range(8):
                r, g, b = pixels[y * 8 + x]
                if (r, g, b) == (0, 0, 0):
                    cells.append("\x1b[0m. ")
                else:
                    cells.append(f"\x1b[38;2;{r};{g};{b}m██")
            lines.append("".join(cells) + "\x1b[0m")
        print("\n".join(lines) + "\n" + "-" * 16)
