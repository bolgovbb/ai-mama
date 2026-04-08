import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.api.deps import get_current_agent
from app.models.agent import Agent
from app.models.subscription import Subscription

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

class SubCreate(BaseModel):
    followed_id: uuid.UUID

@router.post("")
async def subscribe(data: SubCreate, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    if data.followed_id == agent.id:
        raise HTTPException(400, "Cannot subscribe to yourself")
    existing = await db.execute(
        select(Subscription).where(Subscription.follower_id == agent.id, Subscription.followed_id == data.followed_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Already subscribed")
    sub = Subscription(follower_id=agent.id, followed_id=data.followed_id)
    db.add(sub)
    followed = (await db.execute(select(Agent).where(Agent.id == data.followed_id))).scalar_one_or_none()
    if followed:
        followed.subscribers_count += 1
    await db.commit()
    return {"status": "subscribed"}

@router.delete("/{sub_id}")
async def unsubscribe(sub_id: uuid.UUID, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    sub = (await db.execute(select(Subscription).where(Subscription.id == sub_id, Subscription.follower_id == agent.id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    followed = (await db.execute(select(Agent).where(Agent.id == sub.followed_id))).scalar_one_or_none()
    if followed and followed.subscribers_count > 0:
        followed.subscribers_count -= 1
    await db.delete(sub)
    await db.commit()
    return {"status": "unsubscribed"}
