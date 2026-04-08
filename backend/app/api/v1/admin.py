import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.article import Article
from app.services.rag import detect_cascade

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/cascade-alerts")
async def cascade_alerts(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get articles at risk of misinformation cascade."""
    result = await db.execute(
        select(Article)
        .where(Article.status == "published")
        .order_by(desc(Article.reactions_count))
        .limit(limit * 2)
    )
    articles = result.scalars().all()
    alerts = []
    for a in articles:
        cascade = await detect_cascade(
            str(a.id),
            a.reactions_count or 0,
            a.comments_count or 0,
            a.factcheck_score or 50.0,
        )
        if cascade["flagged"]:
            alerts.append({
                "article_id": str(a.id),
                "title": a.title,
                "slug": a.slug,
                "factcheck_score": a.factcheck_score,
                "reactions_count": a.reactions_count,
                "risk_score": cascade["risk_score"],
                "reason": cascade["reason"],
            })
    return {"alerts": alerts[:limit], "total": len(alerts)}

@router.get("/stats")
async def platform_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    from app.models.agent import Agent
    agents_count = (await db.execute(select(func.count(Agent.id)))).scalar()
    articles_count = (await db.execute(
        select(func.count(Article.id)).where(Article.status == "published")
    )).scalar()
    avg_factcheck = (await db.execute(
        select(func.avg(Article.factcheck_score)).where(Article.status == "published")
    )).scalar()
    return {
        "agents": agents_count,
        "published_articles": articles_count,
        "avg_factcheck_score": round(float(avg_factcheck or 0), 1),
    }
