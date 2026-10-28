from typing import Optional
from app.models import Repository
from app.cache.repository import CachedRepo


def repo_to_model(cached: CachedRepo) -> Repository:
    import json
    raw = json.loads(cached.raw_json)
    return Repository(
        id=cached.id,
        name=raw["name"],
        full_name=raw["full_name"],
        description=raw.get("description"),
        language=cached.language,
        stargazers_count=cached.stargazers_count,
        forks_count=cached.forks_count,
        is_fork=cached.is_fork,
        is_archived=cached.is_archived,
        html_url=raw["html_url"],
        updated_at=cached.updated_at,
        created_at=datetime.fromisoformat(raw["created_at"].replace("Z", "+00:00")) if raw.get("created_at") else cached.updated_at,
        topics=raw.get("topics", []),
    )


def filter_repos(
    repos: list[Repository],
    language: Optional[str] = None,
    min_stars: Optional[int] = None,
    max_stars: Optional[int] = None,
    min_forks: Optional[int] = None,
    is_fork: Optional[bool] = None,
    is_archived: Optional[bool] = None,
) -> list[Repository]:
    result = repos
    if language:
        result = [r for r in result if r.language and r.language.lower() == language.lower()]
    if min_stars is not None:
        result = [r for r in result if r.stargazers_count >= min_stars]
    if max_stars is not None:
        result = [r for r in result if r.stargazers_count <= max_stars]
    if min_forks is not None:
        result = [r for r in result if r.forks_count >= min_forks]
    if is_fork is not None:
        result = [r for r in result if r.is_fork == is_fork]
    if is_archived is not None:
        result = [r for r in result if r.is_archived == is_archived]
    return result


def sort_repos(repos: list[Repository], sort: str) -> list[Repository]:
    if sort == "stars_desc":
        return sorted(repos, key=lambda r: r.stargazers_count, reverse=True)
    elif sort == "forks_desc":
        return sorted(repos, key=lambda r: r.forks_count, reverse=True)
    elif sort == "updated_desc":
        return sorted(repos, key=lambda r: r.updated_at, reverse=True)
    elif sort == "created_desc":
        return sorted(repos, key=lambda r: r.created_at, reverse=True)
    return repos


def paginate(items: list, page: int, per_page: int) -> tuple[list, int, int, int]:
    total = len(items)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], total, page, total_pages


from datetime import datetime