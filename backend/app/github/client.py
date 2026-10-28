import httpx
from typing import Optional
import structlog

from app.config import get_settings
from app.api.errors import APIError

logger = structlog.get_logger()


class GitHubClient:
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            base_url=self.settings.github_api_base,
            headers={
                "Authorization": f"token {self.settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def close(self):
        await self.client.aclose()

    def _handle_rate_limit(self, response: httpx.Response) -> Optional[int]:
        """Extract retry-after from rate limit headers. Returns seconds until reset."""
        if response.status_code == 403 and "rate limit" in response.text.lower():
            reset = response.headers.get("X-RateLimit-Reset")
            if reset:
                import time
                return max(int(reset) - int(time.time()), 1)
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                return int(retry_after)
            reset = response.headers.get("X-RateLimit-Reset")
            if reset:
                import time
                return max(int(reset) - int(time.time()), 1)
        return None

    async def get_user(self, username: str) -> dict:
        response = await self.client.get(f"/users/{username}")
        if response.status_code == 404:
            raise APIError("USER_NOT_FOUND", f"User '{username}' not found", 404)
        if response.status_code == 403:
            retry_after = self._handle_rate_limit(response)
            if retry_after:
                raise APIError("RATE_LIMITED", "GitHub API rate limit exceeded", 429, retry_after=retry_after)
            raise APIError("USER_PRIVATE", f"User '{username}' is private or access denied", 403)
        response.raise_for_status()
        return response.json()

    async def get_user_repos(self, username: str, per_page: int = 100) -> list[dict]:
        all_repos = []
        page = 1
        while True:
            response = await self.client.get(
                f"/users/{username}/repos",
                params={"per_page": per_page, "page": page, "sort": "updated", "direction": "desc"},
            )
            if response.status_code == 403:
                retry_after = self._handle_rate_limit(response)
                if retry_after:
                    raise APIError("RATE_LIMITED", "GitHub API rate limit exceeded", 429, retry_after=retry_after)
                raise APIError("UPSTREAM_ERROR", "GitHub API access denied", 502)
            response.raise_for_status()
            repos = response.json()
            if not repos:
                break
            all_repos.extend(repos)
            if len(repos) < per_page:
                break
            page += 1
        return all_repos

    async def get_repo_languages(self, owner: str, repo: str) -> dict[str, int]:
        response = await self.client.get(f"/repos/{owner}/{repo}/languages")
        if response.status_code == 403:
            retry_after = self._handle_rate_limit(response)
            if retry_after:
                raise APIError("RATE_LIMITED", "GitHub API rate limit exceeded", 429, retry_after=retry_after)
        response.raise_for_status()
        return response.json()


github_client = GitHubClient()