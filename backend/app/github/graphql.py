import httpx
from typing import Optional
import structlog

from app.config import get_settings
from app.api.errors import APIError

logger = structlog.get_logger()


CONTRIBUTIONS_QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""


class GraphQLClient:
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            base_url=self.settings.github_graphql_url,
            headers={
                "Authorization": f"Bearer {self.settings.github_token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    async def close(self):
        await self.client.aclose()

    def _handle_rate_limit(self, response: httpx.Response) -> Optional[int]:
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                return int(retry_after)
        # GraphQL returns 200 with errors array for rate limits
        try:
            data = response.json()
            if "errors" in data:
                for error in data["errors"]:
                    if error.get("type") == "RATE_LIMITED":
                        return 60  # default fallback
        except Exception:
            pass
        return None

    async def get_contributions(self, username: str) -> dict:
        response = await self.client.post(
            "",
            json={"query": CONTRIBUTIONS_QUERY, "variables": {"username": username}},
        )
        if response.status_code == 401:
            raise APIError("UPSTREAM_ERROR", "GitHub GraphQL authentication failed", 502)
        if response.status_code == 429:
            retry_after = self._handle_rate_limit(response)
            raise APIError("RATE_LIMITED", "GitHub GraphQL rate limit exceeded", 429, retry_after=retry_after)
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            logger.warning("graphql_errors", errors=data["errors"], username=username)
            # Check for rate limit in errors
            for error in data["errors"]:
                if error.get("type") == "RATE_LIMITED":
                    raise APIError("RATE_LIMITED", "GitHub GraphQL rate limit exceeded", 429, retry_after=60)
        return data.get("data", {})


graphql_client = GraphQLClient()