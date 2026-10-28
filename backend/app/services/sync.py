import asyncio
import structlog
from datetime import datetime

from app.github.client import github_client
from app.github.graphql import graphql_client
from app.cache.repository import (
    upsert_user, upsert_repos, upsert_contributions,
    get_user, is_stale
)
from app.config import get_settings
from app.api.errors import APIError

logger = structlog.get_logger()
settings = get_settings()


async def sync_user(username: str, force: bool = False) -> dict:
    """Sync a single user's data from GitHub."""
    username = username.lower()

    # Check if we should skip (not forced and not stale)
    if not force:
        profile_stale = await is_stale(username, settings.cache_ttl_profile)
        if not profile_stale:
            logger.debug("sync_skipped_not_stale", username=username)
            return {"status": "skipped", "reason": "not_stale", "username": username}

    try:
        # Fetch profile
        profile = await github_client.get_user(username)
        await upsert_user(username, profile, etag=None)  # TODO: extract etag

        # Fetch repos
        repos = await github_client.get_user_repos(username)
        await upsert_repos(username, repos)

        # Fetch contributions
        try:
            contrib_data = await graphql_client.get_contributions(username)
            if contrib_data and "user" in contrib_data and contrib_data["user"]:
                await upsert_contributions(username, contrib_data)
        except APIError as e:
            if e.code != "RATE_LIMITED":
                logger.warning("contributions_fetch_failed", username=username, error=str(e))

        logger.info("sync_completed", username=username, repos=len(repos))
        return {"status": "completed", "username": username, "repos_synced": len(repos), "synced_at": datetime.utcnow().isoformat()}

    except APIError:
        raise
    except Exception as e:
        logger.error("sync_failed", username=username, error=str(e))
        raise APIError("UPSTREAM_ERROR", f"Sync failed: {str(e)}", 502)


async def background_sync() -> None:
    """Background job to sync recently queried users."""
    logger.info("background_sync_started")
    # TODO: Track recently queried users and sync them
    # For now, this is a placeholder
    logger.info("background_sync_completed")


sync_service = {"sync_user": sync_user, "background_sync": background_sync}