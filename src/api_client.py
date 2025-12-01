"""Claude API client for fetching usage data."""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class ClaudeAPIError(Exception):
    """Base exception for API errors."""

    pass


class AuthenticationError(ClaudeAPIError):
    """Cookie expired or invalid."""

    pass


class RateLimitError(ClaudeAPIError):
    """Too many requests."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limited, retry after {retry_after}s")


class NetworkError(ClaudeAPIError):
    """Network connectivity issues."""

    pass


class ClaudeAPIClient:
    """Client for interacting with Claude.ai API."""

    BASE_URL = "https://claude.ai/api"

    def __init__(self, org_id: str, session_cookie: str):
        """
        Initialize API client.

        Args:
            org_id: Organization ID from Claude.ai
            session_cookie: Session cookie value from browser
        """
        self.org_id = org_id
        self.session = requests.Session()
        self._setup_session(session_cookie)
        self._consecutive_failures = 0

    def _setup_session(self, session_cookie: str) -> None:
        """Configure session with authentication and headers."""
        self.session.cookies.set("sessionKey", session_cookie, domain="claude.ai")
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def get_usage(self) -> dict[str, Any]:
        """
        Fetch current usage data from Claude.ai.

        Returns:
            Dict containing usage data with keys like 'five_hour', 'seven_day', etc.

        Raises:
            AuthenticationError: Cookie expired (401/403)
            RateLimitError: Too many requests (429)
            NetworkError: Connection issues
            ClaudeAPIError: Other API errors
        """
        url = f"{self.BASE_URL}/organizations/{self.org_id}/usage"

        try:
            logger.debug(f"Fetching usage from {url}")
            resp = self.session.get(url, timeout=15)

            if resp.status_code in (401, 403):
                logger.warning(f"Authentication failed: {resp.status_code}")
                raise AuthenticationError("Session cookie expired or invalid")

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, retry after {retry_after}s")
                raise RateLimitError(retry_after)

            resp.raise_for_status()
            self._consecutive_failures = 0

            data = resp.json()
            logger.debug(f"Usage data: {data}")
            return data

        except requests.exceptions.ConnectionError as e:
            self._consecutive_failures += 1
            logger.error(f"Connection error: {e}")
            raise NetworkError(f"Connection failed: {e}")

        except requests.exceptions.Timeout:
            self._consecutive_failures += 1
            logger.error("Request timed out")
            raise NetworkError("Request timed out")

        except requests.exceptions.RequestException as e:
            self._consecutive_failures += 1
            logger.error(f"Request failed: {e}")
            raise ClaudeAPIError(f"Request failed: {e}")

    def update_cookie(self, session_cookie: str) -> None:
        """Update the session cookie."""
        self.session.cookies.set("sessionKey", session_cookie, domain="claude.ai")
        logger.info("Session cookie updated")

    @property
    def consecutive_failures(self) -> int:
        """Number of consecutive API failures."""
        return self._consecutive_failures
