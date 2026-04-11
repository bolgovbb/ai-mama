import hashlib
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.agent import Agent

STAFF_ROLES = ("editor", "moderator", "admin")


async def get_current_agent(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> Agent:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    api_key = authorization[7:]
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    result = await db.execute(select(Agent).where(Agent.api_key_hash == key_hash))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(401, "Invalid API key")
    return agent


async def get_staff_agent(
    agent: Agent = Depends(get_current_agent),
) -> Agent:
    if agent.role not in STAFF_ROLES:
        raise HTTPException(403, "Staff access required")
    return agent
