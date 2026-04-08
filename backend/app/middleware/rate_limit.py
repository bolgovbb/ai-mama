import time
from fastapi import Request, HTTPException
from app.config import settings
import redis.asyncio as aioredis

_redis = None

async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis

LIMITS = {
    "POST:/api/v1/articles": (50, 86400),
    "POST:/api/v1/articles/{}/comments": (200, 86400),
    "POST:/api/v1/reactions": (500, 86400),
    "GET": (1000, 3600),
}

async def rate_limit_middleware(request: Request, call_next):
    r = await get_redis()
    path = request.url.path
    method = request.method
    # identify by API key or IP
    auth = request.headers.get("authorization", "")
    key_id = auth[7:23] if auth.startswith("Bearer ") else request.client.host

    # Determine limit
    limit, window = LIMITS.get("GET", (1000, 3600))
    if method == "POST" and "/articles" in path and "/comments" in path:
        limit, window = 200, 86400
    elif method == "POST" and path.endswith("/articles"):
        limit, window = 50, 86400
    elif method == "POST":
        limit, window = 500, 86400

    redis_key = f"rl:{method}:{path}:{key_id}"
    current = await r.get(redis_key)
    current = int(current) if current else 0

    if current >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} requests per {window}s",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(window),
            }
        )

    pipe = r.pipeline()
    await pipe.incr(redis_key)
    await pipe.expire(redis_key, window)
    await pipe.execute()

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current - 1))
    return response
