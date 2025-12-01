"""Pytest fixtures for Claude Usage Monitor tests."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_usage_response():
    """Sample API response for usage endpoint."""
    return {
        "five_hour": {
            "utilization": 47.0,
            "resets_at": "2025-12-01T07:00:00.171939+00:00",
        },
        "seven_day": {
            "utilization": 25.0,
            "resets_at": "2025-12-02T00:00:00.171962+00:00",
        },
        "seven_day_oauth_apps": {"utilization": 0.0, "resets_at": None},
        "seven_day_opus": None,
        "seven_day_sonnet": {
            "utilization": 1.0,
            "resets_at": "2025-12-02T04:00:00+00:00",
        },
        "iguana_necktie": None,
        "extra_usage": None,
    }


@pytest.fixture
def high_usage_response():
    """Sample API response with high usage."""
    return {
        "five_hour": {
            "utilization": 92.0,
            "resets_at": "2025-12-01T07:00:00+00:00",
        },
        "seven_day": {
            "utilization": 78.0,
            "resets_at": "2025-12-02T00:00:00+00:00",
        },
    }


@pytest.fixture
def temp_config_dir():
    """Temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config():
    """Sample configuration dictionary."""
    return {
        "organization_id": "test-org-id-12345",
        "session_cookie": "test-session-cookie-value",
        "poll_interval_seconds": 300,
        "notification_thresholds": [50, 75, 90],
        "start_with_windows": False,
        "debug_mode": False,
    }


@pytest.fixture
def mock_config_file(temp_config_dir, sample_config):
    """Create a mock config file and return its path."""
    config_path = temp_config_dir / "config.json"
    config_path.write_text(json.dumps(sample_config))
    return config_path
