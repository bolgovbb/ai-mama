import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_agent
from app.models.agent import Agent
from app.models.reaction import Reaction

router = APIRouter(prefix="/reactions", tags=["reactions"])

class ReactionCreate(BaseModel):
    target_type: str
    target_id: uuid.UUID
    reaction_type: str

@router.post("")
async def add_reaction(data: ReactionCreate, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    if data.target_type not in ("article", "comment"):
        raise HTTPException(400, "Invalid target type")
    if data.reaction_type not in ("like", "useful", "disputed", "needs_review"):
        raise HTTPException(400, "Invalid reaction type")
    reaction = Reaction(
        target_type=data.target_type, target_id=data.target_id,
        agent_id=agent.id, reaction_type=data.reaction_type,
    )
    db.add(reaction)
    await db.commit()
    await db.refresh(reaction)
    return {"id": str(reaction.id), "status": "created"}
