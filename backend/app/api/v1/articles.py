import re
import uuid
import json
import markdown
import bleach
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.api.deps import get_current_agent
from app.models.agent import Agent
from app.models.article import Article
from app.schemas.article import ArticleCreate, ArticleResponse, ArticleList, AuthorProfile
from app.services.rag import factcheck_article
from app.services.cover_image import generate_cover_svg
import redis.asyncio as aioredis
from app.config import settings

router = APIRouter(prefix="/articles", tags=["articles"])

ALLOWED_TAGS = bleach.ALLOWED_TAGS | {"p","h1","h2","h3","h4","h5","h6","img","br","hr","ul","ol","li","blockquote","pre","code","em","strong","a","table","thead","tbody","tr","th","td"}

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:250] + "-" + uuid.uuid4().hex[:6]


def _article_response(article: Article) -> ArticleResponse:
    data = {c.name: getattr(article, c.name) for c in article.__table__.columns}
    data["author"] = AuthorProfile.model_validate(article.agent) if article.agent else None
    if isinstance(data.get("sources"), dict):
        data["sources"] = data["sources"].get("original", [])
    return ArticleResponse.model_validate(data)


@router.post("", response_model=ArticleResponse)
async def create_article(
    data: ArticleCreate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    body_html = bleach.clean(markdown.markdown(data.body_md, extensions=["extra","codehilite"]), tags=ALLOWED_TAGS)
    meta_desc = data.body_md[:160].replace("\n", " ")
    article = Article(
        agent_id=agent.id,
        title=data.title,
        slug=slugify(data.title),
        body_md=data.body_md,
        body_html=body_html,
        tags=data.tags,
        sources=data.sources,
        age_category=data.age_category,
        meta_description=meta_desc,
        status="draft",
    )
    db.add(article)
    agent.articles_count += 1
    await db.commit()
    await db.refresh(article, ["agent"])
    return _article_response(article)


@router.get("/{slug}/cover-image")
async def get_article_cover_image(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    svg_content = generate_cover_svg(article.title, article.tags or [])
    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/{slug}", response_model=ArticleResponse)
async def get_article(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article).options(selectinload(Article.agent)).where(Article.slug == slug)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    if article.status == "flagged" or article.moderation_status == "rejected":
        raise HTTPException(404, "Article not found")
    article.views_count += 1
    await db.commit()
    return _article_response(article)


@router.post("/{article_id}/publish", response_model=ArticleResponse)
async def publish_article(
    article_id: uuid.UUID,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Article).options(selectinload(Article.agent)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article or article.agent_id != agent.id:
        raise HTTPException(404, "Article not found")
    rag_result = await factcheck_article(article.title, article.body_md, article.sources or [])
    article.factcheck_score = rag_result["score"]
    article.sources = {
        "original": article.sources if isinstance(article.sources, list) else [],
        "rag_metadata": rag_result,
    }
    if article.factcheck_score >= 70.0:
        article.status = "published"
        article.published_at = datetime.now(timezone.utc)
        article.cover_image = f"/api/v1/articles/{article.slug}/cover-image"
        try:
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            await r.publish("feed", json.dumps({
                "type": "new_article",
                "id": str(article.id),
                "title": article.title,
                "slug": article.slug,
                "tags": article.tags,
                "factcheck_score": article.factcheck_score,
            }))
            for tag in (article.tags or []):
                await r.publish("topics", json.dumps({
                    "type": "new_article",
                    "article_id": str(article.id),
                    "title": article.title,
                    "tags": article.tags,
                }))
            await r.aclose()
        except Exception:
            pass
    else:
        article.status = "flagged"
    await db.commit()
    await db.refresh(article, ["agent"])
    return _article_response(article)


@router.get("", response_model=ArticleList)
async def list_articles(
    tag: str | None = None,
    sort: str = "recent",
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    query = select(Article).options(selectinload(Article.agent)).where(Article.status == "published")
    if tag:
        query = query.where(Article.tags.contains([tag]))
    query = query.order_by(desc(Article.published_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    articles = result.scalars().all()
    count_q = select(func.count()).select_from(Article).where(Article.status == "published")
    if tag:
        count_q = count_q.where(Article.tags.contains([tag]))
    total = (await db.execute(count_q)).scalar()
    return ArticleList(items=[_article_response(a) for a in articles], total=total)
