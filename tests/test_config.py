"""Tests for configuration module."""

import json

import pytest

from src.config import ConfigManager, DEFAULT_CONFIG


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_load_existing_config(self, mock_config_file, sample_config):
        """Test loading an existing config file."""
        manager = ConfigManager(config_path=mock_config_file)

        assert manager.config["organization_id"] == sample_config["organization_id"]
        assert manager.config["session_cookie"] == sample_config["session_cookie"]
        assert manager.config["poll_interval_seconds"] == 300

    def test_default_config_on_missing_file(self, temp_config_dir):
        """Test default config is used when file doesn't exist."""
        config_path = temp_config_dir / "nonexistent.json"
        manager = ConfigManager(config_path=config_path)

        assert manager.config["organization_id"] == ""
        assert manager.config["poll_interval_seconds"] == 300
        assert manager.config["notification_thresholds"] == [50, 75, 90]

    def test_merge_with_defaults(self, temp_config_dir):
        """Test that missing config options are filled from defaults."""
        # Create config missing some fields
        partial_config = {"organization_id": "test-org", "session_cookie": "test-cookie"}
        config_path = temp_config_dir / "config.json"
        config_path.write_text(json.dumps(partial_config))

        manager = ConfigManager(config_path=config_path)

        # Should have values from file
        assert manager.config["organization_id"] == "test-org"
        # Should have defaults for missing values
        assert manager.config["poll_interval_seconds"] == 300
        assert "debug_mode" in manager.config

    def test_save_config(self, temp_config_dir, sample_config):
        """Test saving config to file."""
        config_path = temp_config_dir / "config.json"
        manager = ConfigManager(config_path=config_path)
        manager.config = sample_config.copy()

        result = manager.save()

        assert result is True
        assert config_path.exists()

        # Verify saved content
        saved = json.loads(config_path.read_text())
        assert saved["organization_id"] == sample_config["organization_id"]

    def test_is_configured_true(self, mock_config_file):
        """Test is_configured returns True when credentials present."""
        manager = ConfigManager(config_path=mock_config_file)

        assert manager.is_configured() is True

    def test_is_configured_false_empty_org(self, temp_config_dir):
        """Test is_configured returns False when org_id empty."""
        config = {"organization_id": "", "session_cookie": "some-cookie"}
        config_path = temp_config_dir / "config.json"
        config_path.write_text(json.dumps(config))

        manager = ConfigManager(config_path=config_path)

        assert manager.is_configured() is False

    def test_is_configured_false_empty_cookie(self, temp_config_dir):
        """Test is_configured returns False when cookie empty."""
        config = {"organization_id": "some-org", "session_cookie": ""}
        config_path = temp_config_dir / "config.json"
        config_path.write_text(json.dumps(config))

        manager = ConfigManager(config_path=config_path)

        assert manager.is_configured() is False

    def test_dict_access(self, mock_config_file, sample_config):
        """Test dict-like access to config values."""
        manager = ConfigManager(config_path=mock_config_file)

        # __getitem__
        assert manager["organization_id"] == sample_config["organization_id"]

        # __setitem__
        manager["poll_interval_seconds"] = 600
        assert manager["poll_interval_seconds"] == 600

        # __contains__
        assert "organization_id" in manager
        assert "nonexistent_key" not in manager

    def test_get_with_default(self, temp_config_dir):
        """Test get method with default value."""
        config_path = temp_config_dir / "config.json"
        manager = ConfigManager(config_path=config_path)

        # Existing key
        assert manager.get("poll_interval_seconds") == 300

        # Non-existing key with default
        assert manager.get("nonexistent", "default_value") == "default_value"

        # Non-existing key without default
        assert manager.get("nonexistent") is None

    def test_invalid_json_uses_defaults(self, temp_config_dir):
        """Test that invalid JSON falls back to defaults."""
        config_path = temp_config_dir / "config.json"
        config_path.write_text("{ invalid json }")

        manager = ConfigManager(config_path=config_path)

        assert manager.config == DEFAULT_CONFIG
