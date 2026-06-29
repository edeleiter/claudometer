"""Minimal .env loader (no external dependency).

Parses simple ``KEY=VALUE`` lines so you can drop real credentials in a ``.env``
file and test live data on the emulator without editing the JSON config.

Convention (matching python-dotenv): values do NOT override variables already
present in the real environment, so an explicit ``export`` still wins.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _parse(text: str) -> dict:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip matching surrounding quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def load_dotenv(paths) -> dict:
    """Load the given .env files into ``os.environ`` (without overriding).

    Args:
        paths: Iterable of file paths to try, in order. Missing files are skipped.
            Earlier files win over later ones for the same key.

    Returns:
        The merged dict of values that were found (whether or not they were newly
        set in the environment).
    """
    merged: dict[str, str] = {}
    for path in paths:
        if not path:
            continue
        p = Path(path)
        if not p.is_file():
            continue
        try:
            parsed = _parse(p.read_text(encoding="utf-8"))
        except OSError as e:
            logger.debug(f"Could not read {p}: {e}")
            continue
        logger.info(f"Loaded {len(parsed)} value(s) from {p}")
        for key, value in parsed.items():
            merged.setdefault(key, value)
            os.environ.setdefault(key, value)
    return merged
