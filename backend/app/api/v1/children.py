import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.api.deps import get_current_agent
from app.models.agent import Agent
from app.models.child import Child
from app.models.milestone import Milestone
from app.models.observation import DevelopmentObservation
from app.models.recommendation import DevelopmentRecommendation
from app.models.dialog import DialogMessage
from app.schemas.child import (
    ChildCreate, ChildUpdate, ChildResponse,
    ObservationCreate, ObservationResponse,
    RecommendationResponse, MilestoneResponse,
    DevelopmentMap, MapDomain, DialogRequest, DialogResponse
)
from app.services.development import process_dialog, generate_recommendations

router = APIRouter(prefix="/children", tags=["children"])

# ── Children CRUD ──────────────────────────────────────────────────────────────

@router.post("", response_model=ChildResponse)
async def create_child(data: ChildCreate, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    child = Child(agent_id=agent.id, name=data.name, birth_date=data.birth_date, gender=data.gender, metadata_=data.metadata or {})
    db.add(child)
    await db.commit()
    await db.refresh(child)
    return ChildResponse.model_validate(child)

@router.get("", response_model=list[ChildResponse])
async def list_children(agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Child).where(Child.agent_id == agent.id, Child.is_deleted == False))
    return [ChildResponse.model_validate(c) for c in r.scalars().all()]

@router.get("/{child_id}", response_model=ChildResponse)
async def get_child(child_id: uuid.UUID, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id, Child.is_deleted == False))
    child = r.scalar_one_or_none()
    if not child:
        raise HTTPException(404, "Child not found")
    return ChildResponse.model_validate(child)

@router.patch("/{child_id}", response_model=ChildResponse)
async def update_child(child_id: uuid.UUID, data: ChildUpdate, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id, Child.is_deleted == False))
    child = r.scalar_one_or_none()
    if not child:
        raise HTTPException(404, "Child not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(child, k, v)
    child.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(child)
    return ChildResponse.model_validate(child)

@router.delete("/{child_id}")
async def delete_child(child_id: uuid.UUID, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id))
    child = r.scalar_one_or_none()
    if not child:
        raise HTTPException(404, "Child not found")
    child.is_deleted = True
    await db.commit()
    return {"deleted": True}

# ── Development Map ────────────────────────────────────────────────────────────

def _age_months(birth_date) -> int:
    today = date.today()
    return (today.year - birth_date.year) * 12 + (today.month - birth_date.month)

@router.get("/{child_id}/map", response_model=DevelopmentMap)
async def get_map(child_id: uuid.UUID, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id, Child.is_deleted == False))
    child = r.scalar_one_or_none()
    if not child:
        raise HTTPException(404, "Child not found")
    age = _age_months(child.birth_date)
    domains = ["speech", "motor_fine", "motor_gross", "cognitive", "social", "emotional"]
    domain_scores = []
    for domain in domains:
        expected_r = await db.execute(
            select(func.count(Milestone.code)).where(Milestone.domain == domain, Milestone.age_months_max <= age)
        )
        expected = expected_r.scalar() or 0
        achieved_r = await db.execute(
            select(func.count(DevelopmentObservation.id)).where(
                DevelopmentObservation.child_id == child_id,
                DevelopmentObservation.domain == domain,
                DevelopmentObservation.status == "achieved"
            )
        )
        achieved = achieved_r.scalar() or 0
        redflag_r = await db.execute(
            select(func.count(DevelopmentRecommendation.id)).where(
                DevelopmentRecommendation.child_id == child_id,
                DevelopmentRecommendation.domain == domain,
                DevelopmentRecommendation.is_red_flag == True
            )
        )
        red_flags = redflag_r.scalar() or 0
        score = (achieved / expected * 100) if expected > 0 else 0.0
        domain_scores.append(MapDomain(domain=domain, score=round(score, 1), achieved=achieved, expected=expected, red_flags=red_flags))
    overall = sum(d.score for d in domain_scores) / len(domain_scores) if domain_scores else 0.0
    return DevelopmentMap(child_id=child_id, age_months=age, domains=domain_scores, overall_score=round(overall, 1))

# ── Observations ───────────────────────────────────────────────────────────────

@router.post("/{child_id}/observations", response_model=ObservationResponse)
async def add_observation(child_id: uuid.UUID, data: ObservationCreate, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id, Child.is_deleted == False))
    if not r.scalar_one_or_none():
        raise HTTPException(404, "Child not found")
    obs = DevelopmentObservation(child_id=child_id, **data.model_dump())
    db.add(obs)
    await db.commit()
    await db.refresh(obs)
    return ObservationResponse.model_validate(obs)

@router.get("/{child_id}/observations", response_model=list[ObservationResponse])
async def list_observations(child_id: uuid.UUID, domain: Optional[str] = None, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r_c = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id))
    if not r_c.scalar_one_or_none():
        raise HTTPException(404, "Child not found")
    q = select(DevelopmentObservation).where(DevelopmentObservation.child_id == child_id)
    if domain:
        q = q.where(DevelopmentObservation.domain == domain)
    r = await db.execute(q.order_by(DevelopmentObservation.observed_at.desc()))
    return [ObservationResponse.model_validate(o) for o in r.scalars().all()]

# ── Recommendations ────────────────────────────────────────────────────────────

@router.get("/{child_id}/recommendations", response_model=list[RecommendationResponse])
async def get_recommendations(child_id: uuid.UUID, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r_c = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id))
    if not r_c.scalar_one_or_none():
        raise HTTPException(404, "Child not found")
    now = datetime.now(timezone.utc)
    r = await db.execute(
        select(DevelopmentRecommendation).where(
            DevelopmentRecommendation.child_id == child_id,
            (DevelopmentRecommendation.expires_at == None) | (DevelopmentRecommendation.expires_at > now)
        ).order_by(DevelopmentRecommendation.is_red_flag.desc())
    )
    return [RecommendationResponse.model_validate(rec) for rec in r.scalars().all()]

@router.post("/{child_id}/recommendations/refresh", response_model=list[RecommendationResponse])
async def refresh_recommendations(child_id: uuid.UUID, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r_c = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id, Child.is_deleted == False))
    child = r_c.scalar_one_or_none()
    if not child:
        raise HTTPException(404, "Child not found")
    recs = await generate_recommendations(child, db)
    return [RecommendationResponse.model_validate(r) for r in recs]

# ── Dialog ─────────────────────────────────────────────────────────────────────

@router.post("/{child_id}/dialog", response_model=DialogResponse)
async def dialog(child_id: uuid.UUID, req: DialogRequest, agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r_c = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id, Child.is_deleted == False))
    child = r_c.scalar_one_or_none()
    if not child:
        raise HTTPException(404, "Child not found")
    return await process_dialog(child, req.message, agent, db)

@router.get("/{child_id}/dialog/history")
async def dialog_history(child_id: uuid.UUID, limit: int = Query(20, le=100), agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    r_c = await db.execute(select(Child).where(Child.id == child_id, Child.agent_id == agent.id))
    if not r_c.scalar_one_or_none():
        raise HTTPException(404, "Child not found")
    r = await db.execute(select(DialogMessage).where(DialogMessage.child_id == child_id).order_by(DialogMessage.created_at.desc()).limit(limit))
    msgs = r.scalars().all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in reversed(msgs)]

# ── Milestones Reference ───────────────────────────────────────────────────────

@router.get("/milestones/all", response_model=list[MilestoneResponse], tags=["milestones"])
async def list_milestones(domain: Optional[str] = None, age_months: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    q = select(Milestone)
    if domain:
        q = q.where(Milestone.domain == domain)
    if age_months is not None:
        q = q.where(Milestone.age_months_min <= age_months, Milestone.age_months_max >= age_months)
    r = await db.execute(q.order_by(Milestone.domain, Milestone.age_months_min))
    return [MilestoneResponse.model_validate(m) for m in r.scalars().all()]
