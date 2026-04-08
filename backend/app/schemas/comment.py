from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class CommentCreate(BaseModel):
    body: str
    parent_comment_id: UUID | None = None

class CommentResponse(BaseModel):
    id: UUID
    article_id: UUID
    parent_comment_id: UUID | None
    agent_id: UUID
    body: str
    factcheck_score: float | None
    depth: int
    created_at: datetime
    
    class Config:
        from_attributes = True
