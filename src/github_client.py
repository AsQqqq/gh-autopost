import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


class RateLimitError(Exception):
    def __init__(self, reset_at: float):
        self.reset_at = reset_at


class GitHubClient:
    def __init__(self, token: str, max_retries: int = 5, backoff_base: float = 5.0):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._session = requests.Session()
        self._session.headers.update({
            **_HEADERS,
            "Authorization": f"Bearer {token}",
        })

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get(self, url: str, params: dict | None = None) -> Optional[dict | list]:
        for attempt in range(self.max_retries):
            try:
                resp = self._session.get(url, params=params, timeout=30)
            except requests.ConnectionError as exc:
                logger.error(f"Connection error [{attempt+1}/{self.max_retries}]: {exc}")
                self._sleep_backoff(attempt)
                continue
            except requests.Timeout as exc:
                logger.error(f"Timeout [{attempt+1}/{self.max_retries}]: {exc}")
                self._sleep_backoff(attempt)
                continue

            # Rate limit
            if resp.status_code in (403, 429):
                reset_str = resp.headers.get("X-RateLimit-Reset", "")
                try:
                    reset_at = float(reset_str)
                except (ValueError, TypeError):
                    reset_at = time.time() + 60

                wait = max(reset_at - time.time(), 0) + 5
                logger.warning(f"GitHub rate limit hit — waiting {wait:.0f}s before retry")
                time.sleep(wait)
                continue

            if resp.status_code == 404:
                logger.error(f"GitHub 404: {url}")
                return None

            try:
                resp.raise_for_status()
            except requests.HTTPError as exc:
                logger.error(f"GitHub HTTP error [{attempt+1}/{self.max_retries}]: {exc}")
                self._sleep_backoff(attempt)
                continue

            return resp.json()

        logger.error(f"Gave up after {self.max_retries} attempts: {url}")
        return None

    def _sleep_backoff(self, attempt: int):
        delay = self.backoff_base * (attempt + 1)
        logger.info(f"Retrying in {delay:.0f}s…")
        time.sleep(delay)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def get_commits(self, repo: str, branch: str, per_page: int = 100) -> list[dict]:
        """Return list of commit summaries (lightweight, no stats)."""
        url = f"{_BASE}/repos/{repo}/commits"
        result = self._get(url, params={"sha": branch, "per_page": per_page})
        if isinstance(result, list):
            return result
        return []

    def get_commit_detail(self, repo: str, sha: str) -> Optional[dict]:
        """Return full commit object including stats and files."""
        url = f"{_BASE}/repos/{repo}/commits/{sha}"
        result = self._get(url)
        if isinstance(result, dict):
            return result
        return None

    def check_rate_limit(self) -> dict:
        result = self._get(f"{_BASE}/rate_limit")
        if isinstance(result, dict):
            return result.get("rate", {})
        return {}
