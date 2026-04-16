"""Site-wide Кира AI chat: suggestions + ask across the whole AI Mama journal.

Mirrors the per-article endpoints (articles.py `/{slug}/suggestions` + `/{slug}/ask`)
but grounds Кира in a catalogue of the top published articles instead of a single body.
"""
import json
import re

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.article import Article
from app.services.rag import _call_claude

router = APIRouter(prefix="/ai", tags=["ai"])


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)


class AskResponse(BaseModel):
    answer: str


class SuggestionsResponse(BaseModel):
    questions: list[str]


SITE_KIRA_SYSTEM = (
    "Ты — Кира, AI-ассистент журнала AI Mama (часть платформы KinDAR). "
    "Отвечаешь молодым мамам на вопросы о беременности, родах, новорождённых, "
    "грудном вскармливании, прикорме, развитии и воспитании детей.\n\n"
    "ОБЯЗАТЕЛЬНОЕ ПРАВИЛО ПРО ССЫЛКИ НА ИССЛЕДОВАНИЯ:\n"
    "— Если тема вопроса перекликается со статьёй из КАТАЛОГА ниже — "
    "ВСЕГДА оформляй упоминание как markdown-ссылку ровно в виде "
    "[Название статьи](/articles/slug), используя slug из поля URL в каталоге. "
    "Не придумывай названия и slug'и — только из каталога. Никаких внешних ссылок.\n"
    "— В конце ответа добавь короткое предложение «Чтобы углубиться в тему, "
    "прочитай [Название](/articles/slug)» — 1–2 самых релевантных статьи.\n"
    "— Если в каталоге нет подходящей статьи — не придумывай её и не вставляй ссылки.\n\n"
    "ОСТАЛЬНЫЕ ПРАВИЛА:\n"
    "— Тон: тёплый, уважительный, поддерживающий. Без медицинских советов, "
    "дозировок, диагнозов. Если вопрос требует индивидуальной оценки здоровья — "
    "корректно направляй к врачу.\n"
    "— Длина ответа: 2–6 коротких абзацев или список. По-русски.\n"
    "— Используй **bold** для ключевых слов, markdown-ссылки для статей, "
    "эмодзи в меру (1–2 на ответ).\n"
    "— На провокации, оскорбления или вопросы вне темы материнства — "
    "мягко возвращай в тему журнала."
)


async def _build_articles_catalog(db: AsyncSession, limit: int = 25) -> tuple[str, list[dict]]:
    """Fetch the top-viewed published articles and render them as a compact
    catalogue for Кира. Returns (catalog_text, list_of_article_dicts)."""
    stmt = (
        select(Article)
        .where(Article.status == "published")
        .order_by(desc(Article.views_count), desc(Article.published_at))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    articles = [
        {
            "title": a.title or "",
            "slug": a.slug or "",
            "summary": ((a.meta_description or a.body_md or "").strip()[:280]),
            "tags": list(a.tags or []),
        }
        for a in rows
    ]
    lines = []
    for i, a in enumerate(articles, 1):
        tags = ", ".join(a["tags"][:3]) if a["tags"] else ""
        tag_part = f" — {tags}" if tags else ""
        lines.append(
            f"{i}. «{a['title']}»{tag_part}\n"
            f"   URL: /articles/{a['slug']}\n"
            f"   {a['summary']}"
        )
    catalog = "\n\n".join(lines) if lines else "(каталог пуст)"
    return catalog, articles


@router.get("/suggestions", response_model=SuggestionsResponse)
async def site_suggestions(db: AsyncSession = Depends(get_db)):
    """5 general conversation-starter questions for Кира, based on what's
    actually in the journal. Cached in Redis for 1 day."""
    cache_key = "ai:site:suggestions:v1"
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        cached = await r.get(cache_key)
        await r.aclose()
        if cached:
            return SuggestionsResponse(questions=json.loads(cached))
    except Exception:
        pass

    catalog, articles = await _build_articles_catalog(db, limit=20)
    if not articles:
        return SuggestionsResponse(
            questions=[
                "С чего начать подготовку к родам?",
                "Когда и с чего начинать прикорм?",
                "Как наладить сон малыша?",
                "Что делать при первых зубах?",
                "Как справиться с послеродовой усталостью?",
            ]
        )

    system = (
        "Ты формулируешь вопросы, которые молодая мама могла бы задать AI-ассистенту "
        "журнала AI Mama. Ориентируйся на темы, представленные в каталоге. "
        "Верни СТРОГО JSON-массив из 5 коротких вопросов на русском, "
        "каждый не длиннее 60 символов, без нумерации и кавычек-ёлочек. "
        'Пример: ["Когда начинать прикорм?", "Как пережить регресс сна?", …]. '
        "Только JSON, ничего больше."
    )
    user = f"КАТАЛОГ СТАТЕЙ ЖУРНАЛА:\n\n{catalog}"

    raw = await _call_claude(system, user, max_tokens=400)
    questions: list[str] = []
    if raw:
        m = re.search(r"\[[^\[\]]*\]", raw, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, list):
                    questions = [str(q).strip() for q in parsed if isinstance(q, (str, int, float))]
            except json.JSONDecodeError:
                pass

    # Sanity: trim + dedupe, cap at 5
    seen: set[str] = set()
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
        clean = [
            "Что почитать про первые месяцы жизни?",
            "Как выбрать тему для чтения сегодня?",
            "Что посоветуете про сон малыша?",
            "С чего начать прикорм?",
            "Как пережить материнское выгорание?",
        ]

    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.setex(cache_key, 24 * 3600, json.dumps(clean, ensure_ascii=False))
        await r.aclose()
    except Exception:
        pass

    return SuggestionsResponse(questions=clean)


@router.post("/ask", response_model=AskResponse)
async def site_ask(body: AskRequest, db: AsyncSession = Depends(get_db)):
    """Answer a free-form question using the journal's article catalogue as
    grounding context. Returns a short, warm, source-aware response."""
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Empty question")

    catalog, _ = await _build_articles_catalog(db, limit=25)
    user = (
        "КАТАЛОГ СТАТЕЙ НА САЙТЕ (используй как контекст, не цитируй целиком):\n\n"
        f"{catalog}\n\n---\n\nВОПРОС: {question}"
    )
    answer = (await _call_claude(SITE_KIRA_SYSTEM, user, max_tokens=600) or "").strip()
    if not answer:
        answer = (
            "Сейчас не получилось ответить — попробуй задать вопрос чуть позже "
            "или сформулировать иначе. 🌸"
        )
    return AskResponse(answer=answer)
