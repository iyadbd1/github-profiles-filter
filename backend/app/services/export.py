import csv
import io
from typing import Iterator
from app.models import Repository
from app.services.filter import repo_to_model
from app.cache.repository import CachedRepo


def repos_to_csv(repos: list[Repository]) -> Iterator[str]:
    """Stream CSV rows for repos."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "id", "name", "full_name", "description", "language",
        "stars", "forks", "is_fork", "is_archived",
        "url", "updated_at", "created_at", "topics"
    ])
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    for repo in repos:
        writer.writerow([
            repo.id,
            repo.name,
            repo.full_name,
            repo.description or "",
            repo.language or "",
            repo.stargazers_count,
            repo.forks_count,
            repo.is_fork,
            repo.is_archived,
            repo.html_url,
            repo.updated_at.isoformat() if repo.updated_at else "",
            repo.created_at.isoformat() if repo.created_at else "",
            ", ".join(repo.topics),
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)


def repos_to_json(repos: list[Repository]) -> Iterator[str]:
    """Stream JSON array for repos."""
    yield "["
    for i, repo in enumerate(repos):
        if i > 0:
            yield ","
        import json
        yield json.dumps(repo.model_dump(mode="json"))
    yield "]"


def cached_repos_to_models(cached_repos: list[CachedRepo]) -> list[Repository]:
    return [repo_to_model(r) for r in cached_repos]