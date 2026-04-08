from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class AuthorProfile(BaseModel):
    id: UUID
    name: str
    slug: str
    avatar_url: str | None
    bio: str | None
    specialization: list[str]
    reputation_score: float
    verified: bool

    class Config:
        from_attributes = True


class ArticleCreate(BaseModel):
    title: str = Field(max_length=300)
    body_md: str
    tags: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list, min_length=1)
    age_category: str | None = None


class ArticleResponse(BaseModel):
    id: UUID
    agent_id: UUID
    author: AuthorProfile | None = None
    title: str
    slug: str
    body_md: str
    body_html: str | None
    tags: list[str]
    sources: list[dict]
    age_category: str | None
    factcheck_score: float | None
    status: str
    meta_description: str | None
    cover_image: str | None
    views_count: int
    reactions_count: int
    comments_count: int
    published_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class ArticleList(BaseModel):
    items: list[ArticleResponse]
    total: int
