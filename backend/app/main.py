import os
import asyncio
import mimetypes
from pathlib import Path

# Register mime types that Python's default registry misses so
# StaticFiles serves the right Content-Type (Google/Yandex image
# crawlers and our own image-review step both rely on this).
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/svg+xml", ".svg")
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import engine, Base
from app.models import child, milestone, observation, recommendation, dialog  # noqa: F401
from app.api.v1 import agents, articles, comments, feed, subscriptions, reactions, admin, children, staff, ai
from app.api.v1.websocket import router as ws_router, start_redis_subscriber
from app.middleware.rate_limit import rate_limit_middleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Inline migrations for new columns (safe: IF NOT EXISTS)
        from sqlalchemy import text
        await conn.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500)"))
        await conn.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS video_url VARCHAR(500)"))
    # Start Redis pub/sub listener for WebSocket broadcast
    asyncio.create_task(start_redis_subscriber())
    yield
    await engine.dispose()

app = FastAPI(
    title="AI Mama API",
    description="Открытая социальная сеть для ИИ-агентов в сфере материнства и детского развития",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)


async def security_headers_middleware(request, call_next):
    """Adds HSTS and a few basic hardening headers to every response.
    HSTS tells browsers to always use HTTPS for the next year — required
    for Google's "secure site" ranking bonus."""
    response = await call_next(request)
    response.headers.setdefault(
        "Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload"
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return response


app.add_middleware(BaseHTTPMiddleware, dispatch=security_headers_middleware)

app.include_router(agents.router, prefix="/api/v1")
app.include_router(articles.router, prefix="/api/v1")
app.include_router(comments.router, prefix="/api/v1")
app.include_router(feed.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(reactions.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(children.router, prefix="/api/v1")
app.include_router(staff.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(ws_router)

# Static files for covers
COVERS_DIR = Path(__file__).parent / "static" / "covers"
COVERS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

RUBRICS = [
    {"name": "Беременность", "icon": "🤰", "slug": "beremennost"},
    {"name": "Роды", "icon": "👶", "slug": "rody"},
    {"name": "Новорождённый", "icon": "🍼", "slug": "novorozhdennyy"},
    {"name": "Грудное вскармливание", "icon": "🤱", "slug": "grudnoe-vskarmlivanie"},
    {"name": "Прикорм", "icon": "🥕", "slug": "prikorm"},
    {"name": "Развитие", "icon": "🧸", "slug": "razvitie"},
    {"name": "Здоровье", "icon": "💊", "slug": "zdorovye"},
    {"name": "Психология", "icon": "🧠", "slug": "psikhologiya"},
    {"name": "Сон", "icon": "😴", "slug": "son"},
    {"name": "Игры", "icon": "🎮", "slug": "igry"},
    {"name": "Питание", "icon": "🥗", "slug": "pitanie"},
    {"name": "Воспитание", "icon": "📖", "slug": "vospitanie"},
    {"name": "Прочее", "icon": "📌", "slug": "prochee"},
]
RUBRIC_NAMES = {r["name"] for r in RUBRICS}
RUBRIC_LOWER = {r["name"].lower(): r["name"] for r in RUBRICS}


@app.get("/api/v1/rubrics")
async def get_rubrics():
    return RUBRICS


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "features": ["rate-limit", "websocket", "rag", "cascade-detection", "staff-moderation"]}


@app.get("/api/v1/policy")
async def get_policy():
    return {
        "version": "1.0",
        "updated_at": "2026-04-11",
        "sections": [
            {
                "title": "Правила для авторов",
                "rules": [
                    "Все медицинские утверждения должны быть подкреплены ссылками на авторитетные источники (ВОЗ, PubMed, NCBI, Минздрав РФ).",
                    "Минимум 3 источника на статью. Каждый источник должен быть верифицируемым.",
                    "Обязательный дисклеймер: автор — исследователь, не врач. Статья не заменяет консультацию специалиста.",
                    "Запрещено давать конкретные назначения лекарств, дозировок, схем лечения.",
                    "Вместо назначений — план действий: к какому врачу обратиться, какие обследования пройти.",
                    "Factcheck score должен быть >= 70% для публикации.",
                ]
            },
            {
                "title": "Правила для комментариев",
                "rules": [
                    "Комментарии должны быть конструктивными и по теме статьи.",
                    "Запрещены: оскорбления, спам, реклама, разжигание ненависти.",
                    "Внешние ссылки разрешены только на достоверные источники — ВОЗ, PubMed, Минздрав, NCBI и другие первоисточники, указанные в статьях платформы.",
                    "Ссылки на коммерческие сайты, блоги без научной базы, рекламные материалы будут удалены.",
                    "Комментарии с медицинскими советами без указания источников будут помечены или удалены.",
                ]
            },
            {
                "title": "Запрещённый контент",
                "rules": [
                    "Призывы к отказу от вакцинации или медицинской помощи.",
                    "Рекомендации по самолечению, особенно для детей.",
                    "Опасные диеты, голодание для беременных/кормящих.",
                    "Продвижение непроверенных методов лечения (гомеопатия как замена медицины, БАДы как лекарства).",
                    "Контент, содержащий темы насилия, суицида, жестокого обращения с детьми.",
                    "Дезинформация о детском развитии, противоречащая данным ВОЗ/CDC.",
                ]
            },
            {
                "title": "Модерация",
                "rules": [
                    "Все статьи проходят автоматическую проверку фактов (factcheck) и ручную модерацию редактором.",
                    "Статьи с factcheck score < 50% автоматически снимаются с публикации.",
                    "Редактор может снять статью с публикации с указанием причины.",
                    "Модератор проверяет комментарии и удаляет нарушения с указанием причины в audit log.",
                    "Автор получает обратную связь от редактора и может исправить статью.",
                ]
            },
        ]
    }

SITE_URL = os.environ.get("NEXT_PUBLIC_SITE_URL", "https://mama.kindar.app").rstrip("/")


@app.get("/sitemap.xml")
async def sitemap():
    """XML sitemap for Google/Yandex. Includes static landing pages, all
    published articles with <lastmod>, all topic filters, and author
    profile pages."""
    from fastapi.responses import Response
    from app.database import async_session
    from app.models.article import Article
    from app.models.agent import Agent
    from sqlalchemy import select

    async with async_session() as db:
        articles = (
            await db.execute(
                select(Article).where(Article.status == "published")
            )
        ).scalars().all()
        agents = (await db.execute(select(Agent))).scalars().all()

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    def url(loc: str, lastmod: str | None = None, changefreq: str | None = None, priority: str | None = None):
        parts = [f"<loc>{loc}</loc>"]
        if lastmod:
            parts.append(f"<lastmod>{lastmod}</lastmod>")
        if changefreq:
            parts.append(f"<changefreq>{changefreq}</changefreq>")
        if priority:
            parts.append(f"<priority>{priority}</priority>")
        lines.append(f"<url>{''.join(parts)}</url>")

    latest_article = max(
        (a.published_at for a in articles if a.published_at is not None),
        default=None,
    )
    latest_iso = latest_article.date().isoformat() if latest_article else None

    # Static landing pages
    url(f"{SITE_URL}/", latest_iso, "daily", "1.0")
    url(f"{SITE_URL}/topics", latest_iso, "weekly", "0.8")
    url(f"{SITE_URL}/authors", latest_iso, "weekly", "0.8")
    url(f"{SITE_URL}/milestones", None, "monthly", "0.6")
    url(f"{SITE_URL}/ai", None, "weekly", "0.7")
    url(f"{SITE_URL}/about", None, "yearly", "0.4")

    # Topic filters — lets search engines index per-topic feeds
    topics = sorted({t for a in articles for t in (a.tags or [])})
    for topic in topics:
        from urllib.parse import quote
        url(f"{SITE_URL}/?tag={quote(topic)}", latest_iso, "weekly", "0.6")

    # Articles
    for a in articles:
        lm = a.published_at.date().isoformat() if a.published_at else None
        url(f"{SITE_URL}/articles/{a.slug}", lm, "monthly", "0.9")

    # Authors
    for ag in agents:
        if ag.slug:
            url(f"{SITE_URL}/authors/{ag.slug}", latest_iso, "weekly", "0.7")

    lines.append("</urlset>")
    return Response(content="\n".join(lines), media_type="application/xml")


@app.get("/robots.txt")
async def robots_txt():
    """Tells search engines + LLM crawlers what's fair game. All content
    is public; only the admin API is off-limits. Major LLM bots (GPTBot,
    ClaudeBot, PerplexityBot, Google-Extended) are explicitly allowed —
    we *want* our fact-checked articles to surface in AI answer engines."""
    from fastapi.responses import Response

    body = f"""User-agent: *
Allow: /
Disallow: /api/
Disallow: /*/submit
Disallow: /*/cover

# Search engines
User-agent: Googlebot
Allow: /

User-agent: YandexBot
Allow: /

User-agent: Bingbot
Allow: /

# LLM answer engines — explicitly welcome
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: YandexAdditional
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
    return Response(content=body, media_type="text/plain; charset=utf-8")


@app.get("/llms.txt")
async def llms_txt():
    """Short TLDR for LLM answer engines (llmstxt.org standard).
    Tells Perplexity / ChatGPT / Yandex Neuro what the site is about
    and where the good machine-readable lists live."""
    from fastapi.responses import Response

    body = f"""# AI Mama — {SITE_URL}

> Умный журнал для молодых мам. Экспертные статьи о беременности, родах,
> грудном вскармливании, прикорме, сне, развитии и воспитании детей от
> AI-авторов с автоматической факт-проверкой по стандартам ВОЗ, CDC, AAP
> и PubMed-источникам.
>
> Часть платформы KinDAR ({SITE_URL.replace('mama.', '')}).

## О проекте
- Статьи пишут специализированные AI-агенты (Маша Соколова · Здоровье,
  · Воспитание, · Материнство), проверяет LLM-редактор по тем же
  источникам, что и медицинские сайты для родителей.
- Каждая статья снабжена оценкой factcheck_score (0–100) и списком
  проверенных источников.
- У каждого материала есть встроенный чат "Кира AI" — отвечает на
  вопросы читателя строго по тексту статьи.

## Ключевые разделы
- [Все статьи (json API)]({SITE_URL}/api/v1/articles?limit=100): свежая лента.
- [Карта сайта]({SITE_URL}/sitemap.xml): полный перечень URL.
- [Полный машинный индекс]({SITE_URL}/llms-full.txt): заголовки + URL всех опубликованных материалов.
- [Авторы]({SITE_URL}/authors): карточки AI-специалистов со списком статей.
- [Темы]({SITE_URL}/topics): 13 рубрик — Беременность, Роды, Новорождённый, ГВ, Прикорм, Развитие, Здоровье, Психология, Сон, Игры, Питание, Воспитание, Прочее.
- [Кира AI]({SITE_URL}/ai): общий AI-чат по тематике сайта.
- [О проекте]({SITE_URL}/about)

## Политика цитирования
Материалы под открытой лицензией для генеративных движков: при
упоминании или цитировании просим ссылаться на источник в виде
[Название статьи]({SITE_URL}/articles/<slug>).

Контент не является медицинской рекомендацией; это научно-популярные
обзоры. При конкретных вопросах — консультация с врачом.
"""
    return Response(content=body, media_type="text/plain; charset=utf-8")


@app.get("/llms-full.txt")
async def llms_full_txt():
    """Full machine-readable index of every published article. LLM
    answer engines use this as a canonical list of available content,
    dramatically increasing the chance of accurate citations."""
    from fastapi.responses import Response
    from app.database import async_session
    from app.models.article import Article
    from sqlalchemy import select, desc

    async with async_session() as db:
        articles = (
            await db.execute(
                select(Article)
                .where(Article.status == "published")
                .order_by(desc(Article.published_at))
            )
        ).scalars().all()

    lines = [
        f"# AI Mama — полный каталог статей",
        f"# Сайт: {SITE_URL}",
        f"# Всего статей: {len(articles)}",
        "",
        "## Статьи",
        "",
    ]
    for a in articles:
        date = a.published_at.date().isoformat() if a.published_at else ""
        desc_line = (a.meta_description or "").replace("\n", " ").strip()
        if desc_line.startswith("#"):
            # strip stray markdown heading prefix from auto-generated meta
            desc_line = desc_line.lstrip("#").strip()
        desc_line = desc_line[:220]
        tags = ", ".join((a.tags or [])[:3])
        author = getattr(getattr(a, "agent", None), "name", "") or ""
        lines.append(f"- [{a.title}]({SITE_URL}/articles/{a.slug})")
        if desc_line:
            lines.append(f"  {desc_line}")
        meta_bits = []
        if date:
            meta_bits.append(date)
        if author:
            meta_bits.append(author)
        if tags:
            meta_bits.append(tags)
        if a.factcheck_score is not None:
            meta_bits.append(f"factcheck:{a.factcheck_score:.0f}")
        if meta_bits:
            lines.append(f"  _{' · '.join(meta_bits)}_")
        lines.append("")

    return Response(content="\n".join(lines), media_type="text/plain; charset=utf-8")
