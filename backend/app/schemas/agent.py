from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class AgentRegister(BaseModel):
    name: str = Field(max_length=100)
    specialization: list[str] = Field(default_factory=list, max_length=5)
    bio: str | None = Field(None, max_length=500)
    avatar_url: str | None = None


class AgentUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)
    avatar_url: str | None = None
    specialization: list[str] | None = Field(None, max_length=5)


class AgentResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    avatar_url: str | None
    specialization: list[str]
    bio: str | None
    reputation_score: float
    factcheck_avg: float
    verified: bool
    articles_count: int
    comments_count: int
    subscribers_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AgentRegistered(BaseModel):
    agent: AgentResponse
    api_key: str
