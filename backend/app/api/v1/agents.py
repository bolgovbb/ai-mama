import secrets
import re
import hashlib
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_agent
from app.models.agent import Agent
from app.schemas.agent import AgentRegister, AgentResponse, AgentRegistered, AgentUpdate

router = APIRouter(prefix="/agents", tags=["agents"])

TRANSLIT = {
    "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh","з":"z","и":"i","й":"y",
    "к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f",
    "х":"kh","ц":"ts","ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
    " ":"-"
}

def slugify(text: str) -> str:
    text = text.lower().strip()
    result = []
    for ch in text:
        if ch in TRANSLIT:
            result.append(TRANSLIT[ch])
        elif ch.isascii() and (ch.isalnum() or ch == "-"):
            result.append(ch)
    slug = re.sub(r"-+", "-", "".join(result)).strip("-")
    if not slug:
        slug = uuid.uuid4().hex[:8]
    return slug

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

@router.post("/register", response_model=AgentRegistered)
async def register_agent(data: AgentRegister, db: AsyncSession = Depends(get_db)):
    slug = slugify(data.name)
    existing = await db.execute(select(Agent).where(Agent.slug == slug))
    if existing.scalar_one_or_none():
        slug = slug + "-" + uuid.uuid4().hex[:4]
    api_key = secrets.token_urlsafe(32)
    agent = Agent(
        name=data.name,
        slug=slug,
        specialization=data.specialization,
        bio=data.bio,
        avatar_url=data.avatar_url,
        api_key_hash=hash_api_key(api_key),
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentRegistered(agent=AgentResponse.model_validate(agent), api_key=api_key)


@router.patch("/me", response_model=AgentResponse)
async def update_agent_profile(
    data: AgentUpdate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != agent.name:
        new_slug = slugify(update_data["name"])
        existing = await db.execute(select(Agent).where(Agent.slug == new_slug, Agent.id != agent.id))
        if existing.scalar_one_or_none():
            new_slug = new_slug + "-" + uuid.uuid4().hex[:4]
        agent.slug = new_slug
    for field, value in update_data.items():
        setattr(agent, field, value)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.get("/{slug}", response_model=AgentResponse)
async def get_agent(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.slug == slug))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    return AgentResponse.model_validate(agent)
