from datetime import datetime, timedelta
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, select, func
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import json
import structlog

from app.cache.database import Base, async_session
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class CachedUser(Base):
    __tablename__ = "cached_users"
    username = Column(String(255), primary_key=True)
    raw_json = Column(Text, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    etag = Column(String(255), nullable=True)


class CachedRepo(Base):
    __tablename__ = "cached_repos"
    id = Column(Integer, primary_key=True)
    owner_username = Column(String(255), ForeignKey("cached_users.username"), nullable=False, index=True)
    raw_json = Column(Text, nullable=False)
    language = Column(String(100), nullable=True, index=True)
    stargazers_count = Column(Integer, default=0, nullable=False, index=True)
    forks_count = Column(Integer, default=0, nullable=False)
    is_fork = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, nullable=False, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_repos_owner_lang", "owner_username", "language"),
        Index("idx_repos_owner_stars", "owner_username", "stargazers_count"),
        Index("idx_repos_owner_updated", "owner_username", "updated_at"),
    )


class CachedContributions(Base):
    __tablename__ = "cached_contributions"
    username = Column(String(255), ForeignKey("cached_users.username"), primary_key=True)
    raw_json = Column(Text, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SyncMetadata(Base):
    __tablename__ = "sync_metadata"
    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


async def upsert_user(username: str, raw_json: dict, etag: str | None = None) -> None:
    async with async_session() as session:
        stmt = sqlite_insert(CachedUser).values(
            username=username.lower(),
            raw_json=json.dumps(raw_json),
            fetched_at=datetime.utcnow(),
            etag=etag,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["username"],
            set_=dict(raw_json=stmt.excluded.raw_json, fetched_at=stmt.excluded.fetched_at, etag=stmt.excluded.etag),
        )
        await session.execute(stmt)
        await session.commit()


async def get_user(username: str) -> CachedUser | None:
    async with async_session() as session:
        result = await session.execute(select(CachedUser).where(CachedUser.username == username.lower()))
        return result.scalar_one_or_none()


async def upsert_repos(owner_username: str, repos: list[dict]) -> None:
    async with async_session() as session:
        for repo in repos:
            lang = repo.get("language")
            stmt = sqlite_insert(CachedRepo).values(
                id=repo["id"],
                owner_username=owner_username.lower(),
                raw_json=json.dumps(repo),
                language=lang,
                stargazers_count=repo.get("stargazers_count", 0),
                forks_count=repo.get("forks_count", 0),
                is_fork=repo.get("fork", False),
                is_archived=repo.get("archived", False),
                updated_at=datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00")) if repo.get("updated_at") else datetime.utcnow(),
                fetched_at=datetime.utcnow(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=dict(
                    raw_json=stmt.excluded.raw_json,
                    language=stmt.excluded.language,
                    stargazers_count=stmt.excluded.stargazers_count,
                    forks_count=stmt.excluded.forks_count,
                    is_fork=stmt.excluded.is_fork,
                    is_archived=stmt.excluded.is_archived,
                    updated_at=stmt.excluded.updated_at,
                    fetched_at=stmt.excluded.fetched_at,
                ),
            )
            await session.execute(stmt)
        await session.commit()


async def get_repos(
    owner_username: str,
    language: str | None = None,
    min_stars: int | None = None,
    max_stars: int | None = None,
    min_forks: int | None = None,
    is_fork: bool | None = None,
    is_archived: bool | None = None,
    sort: str = "stars_desc",
    page: int = 1,
    per_page: int = 30,
) -> tuple[list[CachedRepo], int]:
    async with async_session() as session:
        stmt = select(CachedRepo).where(CachedRepo.owner_username == owner_username.lower())

        if language:
            stmt = stmt.where(CachedRepo.language == language)
        if min_stars is not None:
            stmt = stmt.where(CachedRepo.stargazers_count >= min_stars)
        if max_stars is not None:
            stmt = stmt.where(CachedRepo.stargazers_count <= max_stars)
        if min_forks is not None:
            stmt = stmt.where(CachedRepo.forks_count >= min_forks)
        if is_fork is not None:
            stmt = stmt.where(CachedRepo.is_fork == is_fork)
        if is_archived is not None:
            stmt = stmt.where(CachedRepo.is_archived == is_archived)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(count_stmt)).scalar()

        # Sort
        if sort == "stars_desc":
            stmt = stmt.order_by(CachedRepo.stargazers_count.desc())
        elif sort == "forks_desc":
            stmt = stmt.order_by(CachedRepo.forks_count.desc())
        elif sort == "updated_desc":
            stmt = stmt.order_by(CachedRepo.updated_at.desc())
        elif sort == "created_desc":
            stmt = stmt.order_by(CachedRepo.id.desc())  # proxy for created

        # Paginate
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await session.execute(stmt)
        repos = result.scalars().all()

        return list(repos), total


async def upsert_contributions(username: str, raw_json: dict) -> None:
    async with async_session() as session:
        stmt = sqlite_insert(CachedContributions).values(
            username=username.lower(),
            raw_json=json.dumps(raw_json),
            fetched_at=datetime.utcnow(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["username"],
            set_=dict(raw_json=stmt.excluded.raw_json, fetched_at=stmt.excluded.fetched_at),
        )
        await session.execute(stmt)
        await session.commit()


async def get_contributions(username: str) -> CachedContributions | None:
    async with async_session() as session:
        result = await session.execute(select(CachedContributions).where(CachedContributions.username == username.lower()))
        return result.scalar_one_or_none()


async def get_cache_stats() -> dict:
    async with async_session() as session:
        users = (await session.execute(select(func.count(CachedUser.username)))).scalar()
        repos = (await session.execute(select(func.count(CachedRepo.id)))).scalar()
        contribs = (await session.execute(select(func.count(CachedContributions.username)))).scalar()
        return {"users": users, "repos": repos, "contributions": contribs}


async def is_stale(username: str, ttl_seconds: int) -> bool:
    """Check if cached data is older than TTL."""
    user = await get_user(username)
    if not user:
        return True
    age = (datetime.utcnow() - user.fetched_at).total_seconds()
    return age > ttl_seconds