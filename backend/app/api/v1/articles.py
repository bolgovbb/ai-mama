import re
import uuid
import json
import markdown
import bleach
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.api.deps import get_current_agent
from app.models.agent import Agent
from app.models.article import Article
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticleResponse, ArticleList, AuthorProfile
from app.services.rag import factcheck_article, _call_claude
from app.services.cover_image import generate_cover_svg
import redis.asyncio as aioredis
from app.config import settings
from pydantic import BaseModel, Field

router = APIRouter(prefix="/articles", tags=["articles"])

ALLOWED_TAGS = bleach.ALLOWED_TAGS | {"p","h1","h2","h3","h4","h5","h6","img","br","hr","ul","ol","li","blockquote","pre","code","em","strong","a","table","thead","tbody","tr","th","td"}

_TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
    'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
    'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
    'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}
_FILLER = {'как','что','это','при','для','от','на','и','в','с','не','из','по',
           'когда','зачем','или','vs','ли','а','то','же','бы','но','за','до',
           'со','об','без','над','под','про','между','через','после','перед','о'}


def slugify(text: str) -> str:
    transliterated = ''.join(_TRANSLIT.get(c, c) for c in text.lower())
    cleaned = re.sub(r'[^a-z0-9\s]+', ' ', transliterated)
    words = [w for w in cleaned.split() if w and w not in _FILLER][:6]
    slug = '-'.join(words)
    if len(slug) > 60:
        slug = slug[:60].rsplit('-', 1)[0]
    return slug or uuid.uuid4().hex[:8]


def _normalize_sources(raw) -> list:
    """Normalize sources to list[dict] regardless of input format."""
    if isinstance(raw, dict):
        raw = raw.get("original", [])
    if not isinstance(raw, list):
        return []
    result = []
    for s in raw:
        if isinstance(s, str) and s.strip():
            result.append({"url": s.strip(), "title": ""})
        elif isinstance(s, dict) and s.get("url"):
            result.append(s)
    return result


def _normalize_tags(tags: list[str]) -> list[str]:
    """Normalize tags to match rubricator. Unknown tags → 'Прочее'."""
    from app.main import RUBRIC_LOWER, RUBRIC_NAMES
    result = []
    seen = set()
    for tag in (tags or []):
        canonical = RUBRIC_LOWER.get(tag.strip().lower())
        if canonical and canonical not in seen:
            result.append(canonical)
            seen.add(canonical)
    if not result:
        result.append("Прочее")
    return result


def _article_response(article: Article) -> ArticleResponse:
    data = {c.name: getattr(article, c.name) for c in article.__table__.columns}
    data["author"] = AuthorProfile.model_validate(article.agent) if article.agent else None
    data["sources"] = _normalize_sources(data.get("sources"))
    data["is_verified"] = (article.status == "published" and article.reviewed_by is not None)
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
        tags=_normalize_tags(data.tags),
        sources=_normalize_sources(data.sources),
        age_category=data.age_category,
        meta_description=meta_desc,
        status="draft",
    )
    db.add(article)
    agent.articles_count += 1
    await db.commit()
    await db.refresh(article, ["agent"])
    return _article_response(article)


@router.get("/search")
async def search_articles(
    q: str = Query(..., min_length=2),
    limit: int = Query(8, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Поиск статей по заголовку и тексту."""
    from sqlalchemy import or_, cast, String
    search_term = f"%{q.lower()}%"
    result = await db.execute(
        select(Article).options(selectinload(Article.agent))
        .where(
            Article.status == "published",
            or_(
                func.lower(Article.title).like(search_term),
                func.lower(Article.body_md).like(search_term),
                func.lower(cast(Article.tags, String)).like(search_term),
            )
        )
        .order_by(desc(Article.views_count))
        .limit(limit)
    )
    articles = result.scalars().all()
    return {"items": [_article_response(a) for a in articles], "total": len(articles)}


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
    if article.status != "published" or article.moderation_status == "rejected":
        raise HTTPException(404, "Article not found")
    article.views_count += 1
    await db.commit()
    return _article_response(article)


@router.post("/{article_id}/submit", response_model=ArticleResponse)
async def submit_article(
    article_id: uuid.UUID,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Отправить статью на проверку. Factcheck → если score ≥ 50 → review, иначе draft."""
    result = await db.execute(
        select(Article).options(selectinload(Article.agent)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article or article.agent_id != agent.id:
        raise HTTPException(404, "Article not found")
    if article.status not in ("draft", "revision"):
        raise HTTPException(400, f"Cannot submit article in status '{article.status}'")

    # Normalize sources before factcheck (handle dict from previous submit)
    original_sources = _normalize_sources(article.sources)
    rag_result = await factcheck_article(article.title, article.body_md, original_sources)
    article.factcheck_score = rag_result["score"]
    article.sources = {
        "original": original_sources,
        "rag_metadata": rag_result,
    }
    # Cover is generated by Flux in deploy_agents.py, not here

    if article.factcheck_score >= 50.0:
        article.status = "review"
        article.moderation_note = None
        article.reviewed_by = None
        article.reviewed_at = None
    else:
        article.status = "draft"
        article.moderation_note = f"Factcheck score {article.factcheck_score:.0f}% — недостаточно для отправки на проверку. Добавьте источники и дисклеймер."

    await db.commit()
    await db.refresh(article, ["agent"])
    return _article_response(article)


@router.get("/my/revisions", response_model=list[ArticleResponse])
async def my_revisions(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Статьи текущего агента со статусом revision (возвращены на доработку)."""
    result = await db.execute(
        select(Article).options(selectinload(Article.agent))
        .where(Article.agent_id == agent.id, Article.status == "revision")
        .order_by(Article.created_at)
    )
    return [_article_response(a) for a in result.scalars().all()]


@router.patch("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: uuid.UUID,
    data: ArticleUpdate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Обновить статью. Если published — сбрасывает в review для повторной проверки."""
    result = await db.execute(
        select(Article).options(selectinload(Article.agent)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article or article.agent_id != agent.id:
        raise HTTPException(404, "Article not found")
    if article.status == "review":
        raise HTTPException(400, "Article is under review, cannot edit")

    if data.title is not None:
        article.title = data.title
    if data.body_md is not None:
        article.body_md = data.body_md
        article.body_html = bleach.clean(
            markdown.markdown(data.body_md, extensions=["extra", "codehilite"]),
            tags=ALLOWED_TAGS
        )
    if data.tags is not None:
        article.tags = _normalize_tags(data.tags)
    if data.sources is not None:
        article.sources = _normalize_sources(data.sources)
    if data.age_category is not None:
        article.age_category = data.age_category

    # Если статья была published — сбросить в review для повторной проверки
    if article.status == "published":
        article.status = "review"
        article.reviewed_by = None
        article.reviewed_at = None
        article.moderation_note = "Статья изменена после публикации — требует повторной проверки."

    await db.commit()
    await db.refresh(article, ["agent"])
    return _article_response(article)


@router.post("/{article_id}/cover")
async def upload_cover(
    article_id: uuid.UUID,
    file: UploadFile = File(...),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Загрузить обложку статьи. Автор или staff."""
    from app.api.deps import STAFF_ROLES
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    if article.agent_id != agent.id and agent.role not in STAFF_ROLES:
        raise HTTPException(403, "Not your article")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "webp"
    covers_dir = Path(__file__).parent.parent.parent / "static" / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{article_id}.{ext}"
    filepath = covers_dir / filename

    content = await file.read()
    filepath.write_bytes(content)

    article.cover_image = f"/static/covers/{filename}"
    await db.commit()

    return {"cover_image": article.cover_image, "size": len(content)}


@router.post("/{article_id}/audio")
async def upload_audio(
    article_id: uuid.UUID,
    file: UploadFile = File(...),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Загрузить аудиоподкаст статьи. Автор или staff."""
    from app.api.deps import STAFF_ROLES
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    if article.agent_id != agent.id and agent.role not in STAFF_ROLES:
        raise HTTPException(403, "Not your article")

    audio_dir = Path(__file__).parent.parent.parent / "static" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{article_id}.mp3"
    filepath = audio_dir / filename

    content = await file.read()
    filepath.write_bytes(content)

    article.audio_url = f"/static/audio/{filename}"
    await db.commit()

    return {"audio_url": article.audio_url, "size": len(content)}


@router.get("/tags/popular")
async def popular_tags(limit: int = Query(10, le=50), db: AsyncSession = Depends(get_db)):
    """Популярные теги по количеству статей."""
    result = await db.execute(
        select(Article.tags).where(Article.status == "published")
    )
    tag_counts: dict[str, int] = {}
    for row in result.fetchall():
        for tag in (row[0] or []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:limit]
    return [{"tag": t, "count": c} for t, c in sorted_tags]


@router.get("/top/articles")
async def top_articles(limit: int = Query(3, le=10), days: int = Query(3, le=30), db: AsyncSession = Depends(get_db)):
    """Топ статей по просмотрам."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Article).options(selectinload(Article.agent))
        .where(Article.status == "published", Article.published_at >= cutoff)
        .order_by(desc(Article.views_count)).limit(limit)
    )
    articles = result.scalars().all()
    if len(articles) < limit:
        result = await db.execute(
            select(Article).options(selectinload(Article.agent))
            .where(Article.status == "published")
            .order_by(desc(Article.views_count)).limit(limit)
        )
        articles = result.scalars().all()
    return [{"title": a.title, "slug": a.slug, "views_count": a.views_count, "author_name": a.agent.name if a.agent else "AI"} for a in articles]


@router.get("/top/authors")
async def top_authors(limit: int = Query(3, le=10), days: int = Query(3, le=30), db: AsyncSession = Depends(get_db)):
    """Топ авторов по просмотрам статей."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Agent.name, Agent.slug, func.sum(Article.views_count).label("total_views"), func.count(Article.id).label("articles_count"))
        .join(Article, Article.agent_id == Agent.id)
        .where(Article.status == "published", Article.published_at >= cutoff)
        .group_by(Agent.id, Agent.name, Agent.slug)
        .order_by(desc("total_views")).limit(limit)
    )
    rows = result.fetchall()
    if len(rows) < limit:
        result = await db.execute(
            select(Agent.name, Agent.slug, func.sum(Article.views_count).label("total_views"), func.count(Article.id).label("articles_count"))
            .join(Article, Article.agent_id == Agent.id)
            .where(Article.status == "published")
            .group_by(Agent.id, Agent.name, Agent.slug)
            .order_by(desc("total_views")).limit(limit)
        )
        rows = result.fetchall()
    return [{"name": r.name, "slug": r.slug, "views": r.total_views, "articles": r.articles_count} for r in rows]


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


# ─────────────────────────────────────────────
# Кира AI — Ask-about-this-article chat
# ─────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)


class AskResponse(BaseModel):
    answer: str


class SuggestionsResponse(BaseModel):
    questions: list[str]


KIRA_SYSTEM = (
    "Ты — Кира, AI-помощник журнала AI Mama (часть платформы KinDAR). "
    "Отвечаешь молодым мамам на вопросы ПО КОНКРЕТНОЙ СТАТЬЕ. "
    "Правила:\n"
    "— Отвечай ТОЛЬКО на основе текста статьи, который тебе передан. "
    "Если ответа в статье нет — честно скажи «В этой статье об этом не говорится» "
    "и коротко предложи обратиться к врачу или посмотреть источники в конце статьи.\n"
    "— Тон: тёплый, уважительный, без медицинских советов. "
    "НИКОГДА не назначай дозировки, лечение или диагнозы.\n"
    "— Длина ответа: 2–5 коротких предложений. По-русски.\n"
    "— Не придумывай факты. Не ссылайся на источники, которых нет в статье."
)


def _truncate_article_context(body_md: str, limit: int = 8000) -> str:
    """Trim body to fit the model context budget comfortably."""
    text = (body_md or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[…текст статьи сокращён…]"


@router.get("/{slug}/suggestions", response_model=SuggestionsResponse)
async def article_suggestions(slug: str, db: AsyncSession = Depends(get_db)):
    """Return up to 5 suggested questions a reader might ask about this article.

    Cached in Redis for 7 days per slug.
    """
    cache_key = f"article:suggestions:{slug}"
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        cached = await r.get(cache_key)
        await r.aclose()
        if cached:
            return SuggestionsResponse(questions=json.loads(cached))
    except Exception:
        pass

    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if not article or article.status != "published":
        raise HTTPException(404, "Article not found")

    system = (
        "Ты формулируешь вопросы, которые читатель-мама мог бы задать по статье. "
        "Верни СТРОГО JSON-массив из 5 коротких вопросов на русском, "
        "каждый вопрос не длиннее 60 символов, без нумерации и без кавычек-ёлочек. "
        "Пример ответа: [\"Что такое …?\", \"Когда обращаться к врачу?\", …]. "
        "Только JSON, ничего больше."
    )
    user = f"Заголовок: {article.title}\n\nТекст статьи:\n{_truncate_article_context(article.body_md, 6000)}"

    raw = await _call_claude(system, user, max_tokens=400)
    questions: list[str] = []
    if raw:
        # Robust JSON extraction — sometimes the model wraps in ```json
        m = re.search(r"\[[^\[\]]*\]", raw, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, list):
                    questions = [str(q).strip() for q in parsed if isinstance(q, (str, int, float))]
            except json.JSONDecodeError:
                pass

    # Sanity: trim + dedupe, cap at 5
    seen = set()
    clean: list[str] = []
    for q in questions:
        q = q.strip().strip('"«»').strip()
        if not q or len(q) > 120 or q in seen:
            continue
        if not q.endswith("?"):
            q = q.rstrip(".!") + "?"
        seen.add(q)
        clean.append(q)
        if len(clean) >= 5:
            break

    if not clean:
        # Safe generic fallback so the widget never looks empty
        clean = [
            "Что самое важное в этой статье?",
            "Когда стоит обратиться к врачу?",
            "На каких источниках это основано?",
        ]

    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.setex(cache_key, 7 * 24 * 3600, json.dumps(clean, ensure_ascii=False))
        await r.aclose()
    except Exception:
        pass

    return SuggestionsResponse(questions=clean)


@router.post("/{slug}/ask", response_model=AskResponse)
async def ask_about_article(
    slug: str,
    body: AskRequest,
    db: AsyncSession = Depends(get_db),
):
    """Answer a reader's question using only the article's content as context."""
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if not article or article.status != "published":
        raise HTTPException(404, "Article not found")

    question = body.question.strip()
    user = (
        f"СТАТЬЯ «{article.title}»:\n\n"
        f"{_truncate_article_context(article.body_md, 8000)}\n\n"
        f"---\n\nВОПРОС ЧИТАТЕЛЯ: {question}"
    )

    answer = await _call_claude(KIRA_SYSTEM, user, max_tokens=400)
    answer = (answer or "").strip()
    if not answer:
        answer = (
            "Сейчас не получилось ответить — попробуй задать вопрос чуть позже "
            "или иначе. 🌸"
        )
    return AskResponse(answer=answer)
