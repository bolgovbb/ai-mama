import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import engine, Base
from app.models import child, milestone, observation, recommendation, dialog  # noqa: F401
from app.api.v1 import agents, articles, comments, feed, subscriptions, reactions, admin, children
from app.api.v1.websocket import router as ws_router, start_redis_subscriber
from app.middleware.rate_limit import rate_limit_middleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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

app.include_router(agents.router, prefix="/api/v1")
app.include_router(articles.router, prefix="/api/v1")
app.include_router(comments.router, prefix="/api/v1")
app.include_router(feed.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(reactions.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(children.router, prefix="/api/v1")
app.include_router(ws_router)

@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "features": ["rate-limit", "websocket", "rag", "cascade-detection"]}

@app.get("/sitemap.xml")
async def sitemap():
    from fastapi.responses import Response
    from app.database import async_session
    from app.models.article import Article
    from sqlalchemy import select
    async with async_session() as db:
        result = await db.execute(select(Article).where(Article.status == "published"))
        articles_list = result.scalars().all()
    urls = ['<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for a in articles_list:
        urls.append(f"<url><loc>http://5.129.205.143/articles/{a.slug}</loc></url>")
    urls.append("</urlset>")
    return Response(content="\n".join(urls), media_type="application/xml")
