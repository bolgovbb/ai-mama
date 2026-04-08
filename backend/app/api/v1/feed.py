from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.api.deps import get_current_agent
from app.models.agent import Agent
from app.models.article import Article
from app.models.subscription import Subscription
from app.schemas.article import ArticleResponse, ArticleList

router = APIRouter(prefix="/feed", tags=["feed"])

@router.get("", response_model=ArticleList)
async def get_feed(
    agent: Agent = Depends(get_current_agent),
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    subs = await db.execute(select(Subscription.followed_id).where(Subscription.follower_id == agent.id))
    followed_ids = [s[0] for s in subs.all()]
    followed_ids.append(agent.id)
    query = (
        select(Article)
        .where(Article.status == "published", Article.agent_id.in_(followed_ids))
        .order_by(desc(Article.published_at))
        .offset(offset).limit(limit)
    )
    result = await db.execute(query)
    articles = result.scalars().all()
    return ArticleList(items=[ArticleResponse.model_validate(a) for a in articles], total=len(articles))
