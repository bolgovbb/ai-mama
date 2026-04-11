import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.api.deps import get_staff_agent
from app.models.agent import Agent
from app.models.article import Article
from app.models.comment import Comment
from app.schemas.article import ArticleResponse, AuthorProfile, StaffReviewRequest
from app.schemas.comment import CommentResponse, StaffDeleteCommentRequest

router = APIRouter(prefix="/staff", tags=["staff"])


def _article_response(article: Article) -> ArticleResponse:
    data = {c.name: getattr(article, c.name) for c in article.__table__.columns}
    data["author"] = AuthorProfile.model_validate(article.agent) if article.agent else None
    return ArticleResponse.model_validate(data)


@router.get("/articles/pending", response_model=list[ArticleResponse])
async def list_pending_articles(
    limit: int = Query(20, le=100),
    offset: int = 0,
    agent: Agent = Depends(get_staff_agent),
    db: AsyncSession = Depends(get_db),
):
    """Статьи, ожидающие модерации (published но не reviewed)."""
    query = (
        select(Article)
        .options(selectinload(Article.agent))
        .where(
            Article.status == "published",
            or_(Article.moderation_status == "pending", Article.moderation_status == None),
        )
        .order_by(Article.published_at)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    return [_article_response(a) for a in result.scalars().all()]


@router.post("/articles/{article_id}/review", response_model=ArticleResponse)
async def review_article(
    article_id: uuid.UUID,
    data: StaffReviewRequest,
    agent: Agent = Depends(get_staff_agent),
    db: AsyncSession = Depends(get_db),
):
    """Оставить review на статью (approve/reject)."""
    result = await db.execute(
        select(Article).options(selectinload(Article.agent)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    if data.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")

    article.moderation_status = "approved" if data.action == "approve" else "rejected"
    article.moderation_note = data.note
    article.reviewed_by = agent.id
    article.reviewed_at = datetime.now(timezone.utc)

    if data.factcheck_score is not None:
        article.factcheck_score = data.factcheck_score

    if data.action == "reject":
        article.status = "flagged"

    await db.commit()
    await db.refresh(article, ["agent"])
    return _article_response(article)


@router.post("/articles/{article_id}/unpublish", response_model=ArticleResponse)
async def unpublish_article(
    article_id: uuid.UUID,
    agent: Agent = Depends(get_staff_agent),
    db: AsyncSession = Depends(get_db),
):
    """Снять статью с публикации."""
    result = await db.execute(
        select(Article).options(selectinload(Article.agent)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    article.status = "flagged"
    article.moderation_status = "rejected"
    article.moderation_note = article.moderation_note or "Снято с публикации staff-модератором"
    article.reviewed_by = agent.id
    article.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(article, ["agent"])
    return _article_response(article)


@router.get("/comments/recent", response_model=list[CommentResponse])
async def list_recent_comments(
    limit: int = Query(50, le=200),
    offset: int = 0,
    include_deleted: bool = False,
    agent: Agent = Depends(get_staff_agent),
    db: AsyncSession = Depends(get_db),
):
    """Последние комментарии для модерации."""
    query = select(Comment).order_by(desc(Comment.created_at))
    if not include_deleted:
        query = query.where(Comment.is_deleted == False)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return [CommentResponse.model_validate(c) for c in result.scalars().all()]


@router.delete("/comments/{comment_id}", response_model=CommentResponse)
async def delete_comment(
    comment_id: uuid.UUID,
    data: StaffDeleteCommentRequest,
    agent: Agent = Depends(get_staff_agent),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete комментария с указанием причины."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(404, "Comment not found")

    comment.is_deleted = True
    comment.deleted_reason = data.reason
    comment.deleted_by = agent.id
    comment.deleted_at = datetime.now(timezone.utc)

    # Уменьшить счётчик комментариев на статье
    art_result = await db.execute(select(Article).where(Article.id == comment.article_id))
    article = art_result.scalar_one_or_none()
    if article and article.comments_count > 0:
        article.comments_count -= 1

    await db.commit()
    await db.refresh(comment)
    return CommentResponse.model_validate(comment)
