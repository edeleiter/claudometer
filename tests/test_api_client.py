"""Tests for API client module."""

import pytest
import responses

from src.api_client import (
    AuthenticationError,
    ClaudeAPIClient,
    ClaudeAPIError,
    NetworkError,
    RateLimitError,
)


class TestClaudeAPIClient:
    """Tests for ClaudeAPIClient class."""

    @responses.activate
    def test_get_usage_success(self, sample_usage_response):
        """Test successful API call returns usage data."""
        responses.add(
            responses.GET,
            "https://claude.ai/api/organizations/test-org/usage",
            json=sample_usage_response,
            status=200,
        )

        client = ClaudeAPIClient("test-org", "test-cookie")
        result = client.get_usage()

        assert result["five_hour"]["utilization"] == 47.0
        assert result["seven_day"]["utilization"] == 25.0
        assert client.consecutive_failures == 0

    @responses.activate
    def test_get_usage_auth_error_401(self):
        """Test 401 response raises AuthenticationError."""
        responses.add(
            responses.GET,
            "https://claude.ai/api/organizations/test-org/usage",
            status=401,
        )

        client = ClaudeAPIClient("test-org", "test-cookie")

        with pytest.raises(AuthenticationError) as exc_info:
            client.get_usage()

        assert "expired" in str(exc_info.value).lower()

    @responses.activate
    def test_get_usage_auth_error_403(self):
        """Test 403 response raises AuthenticationError."""
        responses.add(
            responses.GET,
            "https://claude.ai/api/organizations/test-org/usage",
            status=403,
        )

        client = ClaudeAPIClient("test-org", "test-cookie")

        with pytest.raises(AuthenticationError):
            client.get_usage()

    @responses.activate
    def test_get_usage_rate_limit(self):
        """Test 429 response raises RateLimitError with retry-after."""
        responses.add(
            responses.GET,
            "https://claude.ai/api/organizations/test-org/usage",
            status=429,
            headers={"Retry-After": "120"},
        )

        client = ClaudeAPIClient("test-org", "test-cookie")

        with pytest.raises(RateLimitError) as exc_info:
            client.get_usage()

        assert exc_info.value.retry_after == 120

    @responses.activate
    def test_get_usage_rate_limit_default_retry(self):
        """Test 429 without Retry-After header uses default."""
        responses.add(
            responses.GET,
            "https://claude.ai/api/organizations/test-org/usage",
            status=429,
        )

        client = ClaudeAPIClient("test-org", "test-cookie")

        with pytest.raises(RateLimitError) as exc_info:
            client.get_usage()

        assert exc_info.value.retry_after == 60  # Default

    @responses.activate
    def test_get_usage_server_error(self):
        """Test 500 response raises ClaudeAPIError."""
        responses.add(
            responses.GET,
            "https://claude.ai/api/organizations/test-org/usage",
            status=500,
        )

        client = ClaudeAPIClient("test-org", "test-cookie")

        with pytest.raises(ClaudeAPIError):
            client.get_usage()

    @responses.activate
    def test_consecutive_failures_increment(self):
        """Test consecutive failures counter increments on errors."""
        responses.add(
            responses.GET,
            "https://claude.ai/api/organizations/test-org/usage",
            body=ConnectionError("Network error"),
        )

        client = ClaudeAPIClient("test-org", "test-cookie")

        with pytest.raises(NetworkError):
            client.get_usage()

        assert client.consecutive_failures == 1

    @responses.activate
    def test_consecutive_failures_reset_on_success(self, sample_usage_response):
        """Test consecutive failures counter resets on success."""
        # First call fails
        responses.add(
            responses.GET,
            "https://claude.ai/api/organizations/test-org/usage",
            body=ConnectionError("Network error"),
        )
        # Second call succeeds
        responses.add(
            responses.GET,
            "https://claude.ai/api/organizations/test-org/usage",
            json=sample_usage_response,
            status=200,
        )

        client = ClaudeAPIClient("test-org", "test-cookie")

        with pytest.raises(NetworkError):
            client.get_usage()

        assert client.consecutive_failures == 1

        result = client.get_usage()
        assert result is not None
        assert client.consecutive_failures == 0

    def test_update_cookie(self):
        """Test cookie can be updated."""
        client = ClaudeAPIClient("test-org", "old-cookie")
        client.update_cookie("new-cookie")

        # Check the session has the new cookie
        cookie = client.session.cookies.get("sessionKey", domain="claude.ai")
        assert cookie == "new-cookie"
