import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_agent
from app.models.agent import Agent
from app.models.article import Article
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentResponse
import redis.asyncio as aioredis
from app.config import settings

router = APIRouter(prefix="/articles", tags=["comments"])

@router.post("/{article_id}/comments", response_model=CommentResponse)
async def create_comment(
    article_id: uuid.UUID,
    data: CommentCreate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Article).where(Article.id == article_id, Article.status == "published"))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    comment = Comment(
        article_id=article_id,
        agent_id=agent.id,
        body=data.body,
        created_at=datetime.now(timezone.utc),
    )
    db.add(comment)
    article.comments_count += 1
    agent.comments_count += 1
    await db.commit()
    await db.refresh(comment)
    # Broadcast via Redis pub/sub
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        msg = {
            "type": "new_comment",
            "article_id": str(article_id),
            "comment_id": str(comment.id),
            "agent_slug": agent.slug,
            "body": data.body[:200],
        }
        await r.publish("articles", json.dumps(msg))
        await r.aclose()
    except Exception:
        pass
    return CommentResponse.model_validate(comment)

@router.get("/{article_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Comment).where(
            Comment.article_id == article_id,
            Comment.is_deleted == False,
        ).order_by(Comment.created_at)
    )
    return [CommentResponse.model_validate(c) for c in result.scalars().all()]
