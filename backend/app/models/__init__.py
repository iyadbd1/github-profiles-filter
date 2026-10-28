from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    username: str = Field(alias="login")
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    blog: Optional[str] = None
    twitter_username: Optional[str] = Field(default=None, alias="twitter_username")
    public_repos: int
    followers: int
    following: int
    created_at: datetime
    updated_at: datetime
    avatar_url: str

    class Config:
        populate_by_name = True


class Repository(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stargazers_count: int
    forks_count: int
    is_fork: bool
    is_archived: bool = Field(default=False, alias="archived")
    html_url: str
    updated_at: datetime
    created_at: datetime
    topics: list[str] = []

    class Config:
        populate_by_name = True


class LanguageStats(BaseModel):
    language: str
    bytes: int
    percentage: float


class ContributionDay(BaseModel):
    date: str
    count: int
    level: int  # 0-3


class ContributionWeek(BaseModel):
    first_day: str
    days: list[ContributionDay]


class ContributionHeatmap(BaseModel):
    weeks: list[ContributionWeek]
    total_contributions: int