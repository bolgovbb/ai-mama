import json
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
from app.config import settings

router = APIRouter(tags=["websocket"])

class ConnectionManager:
    def __init__(self):
        self.feed_clients: Set[WebSocket] = set()
        self.article_clients: Dict[str, Set[WebSocket]] = {}
        self.topic_clients: Dict[str, Set[WebSocket]] = {}

    async def connect_feed(self, ws: WebSocket):
        await ws.accept()
        self.feed_clients.add(ws)

    async def connect_article(self, ws: WebSocket, article_id: str):
        await ws.accept()
        self.article_clients.setdefault(article_id, set()).add(ws)

    async def connect_topic(self, ws: WebSocket, tag: str):
        await ws.accept()
        self.topic_clients.setdefault(tag, set()).add(ws)

    def disconnect(self, ws: WebSocket, scope: str = "feed", key: str = None):
        self.feed_clients.discard(ws)
        if key:
            self.article_clients.get(key, set()).discard(ws)
            self.topic_clients.get(key, set()).discard(ws)

    async def broadcast_feed(self, message: dict):
        dead = set()
        for ws in self.feed_clients.copy():
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self.feed_clients -= dead

    async def broadcast_article(self, article_id: str, message: dict):
        dead = set()
        for ws in self.article_clients.get(article_id, set()).copy():
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self.article_clients.get(article_id, set()).difference_update(dead)

    async def broadcast_topic(self, tag: str, message: dict):
        dead = set()
        for ws in self.topic_clients.get(tag, set()).copy():
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self.topic_clients.get(tag, set()).difference_update(dead)

manager = ConnectionManager()
_redis_sub = None

async def start_redis_subscriber():
    global _redis_sub
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("feed", "articles", "topics")
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            data = json.loads(message["data"])
            channel = message["channel"]
            if channel == "feed":
                await manager.broadcast_feed(data)
            elif channel == "articles":
                await manager.broadcast_article(data.get("article_id", ""), data)
            elif channel == "topics":
                for tag in data.get("tags", []):
                    await manager.broadcast_topic(tag, data)
        except Exception:
            pass

@router.websocket("/ws/feed")
async def ws_feed(websocket: WebSocket):
    await manager.connect_feed(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.websocket("/ws/article/{article_id}")
async def ws_article(websocket: WebSocket, article_id: str):
    await manager.connect_article(websocket, article_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "article", article_id)

@router.websocket("/ws/topic/{tag}")
async def ws_topic(websocket: WebSocket, tag: str):
    await manager.connect_topic(websocket, tag)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "topic", tag)
