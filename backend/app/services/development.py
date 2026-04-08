"""Development map AI service: dialog NLU, milestone mapping, recommendations."""
import json, os
from datetime import date, datetime, timezone, timedelta
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.child import Child
from app.models.milestone import Milestone
from app.models.observation import DevelopmentObservation
from app.models.recommendation import DevelopmentRecommendation
from app.models.dialog import DialogMessage
from app.schemas.child import ObservationResponse, DialogResponse

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

async def _claude(system: str, user: str, max_tokens: int = 1024) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return ""
    async with httpx.AsyncClient(timeout=30) as h:
        r = await h.post(ANTHROPIC_URL,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": max_tokens,
                  "system": system, "messages": [{"role": "user", "content": user}]})
        if r.status_code == 200:
            return r.json()["content"][0]["text"]
    return ""

def _age_months(birth_date) -> int:
    today = date.today()
    return (today.year - birth_date.year) * 12 + (today.month - birth_date.month)

async def process_dialog(child: Child, message: str, agent, db: AsyncSession) -> DialogResponse:
    age = _age_months(child.birth_date)
    # Save user message
    db.add(DialogMessage(child_id=child.id, role="user", content=message))

    # NLU: extract observations from message
    system_nlu = (
        "You are a child development assistant. Extract developmental observations from the parent message. "
        "Return JSON array: [{\"domain\": one of speech/motor_fine/motor_gross/cognitive/social/emotional, "
        "\"milestone_code\": short_snake_case_code, \"status\": one of achieved/emerging/not_yet, "
        "\"age_months\": integer, \"confidence\": 0-1}]. "
        "Return empty array [] if no observations found. Return JSON only."
    )
    nlu_raw = await _claude(system_nlu, f"Child age: {age} months. Parent says: {message}")
    observations_extracted = []
    try:
        extracted = json.loads(nlu_raw) if nlu_raw else []
        if not isinstance(extracted, list):
            extracted = []
    except Exception:
        extracted = []

    new_obs_models = []
    red_flags = []
    updated_domains = set()

    for item in extracted:
        try:
            domain = item.get("domain", "")
            milestone_code = item.get("milestone_code", "")
            status = item.get("status", "achieved")
            obs_age = int(item.get("age_months", age))
            confidence = float(item.get("confidence", 0.8))
            if not domain or not milestone_code:
                continue
            obs = DevelopmentObservation(
                child_id=child.id, domain=domain, milestone_code=milestone_code,
                status=status, observed_at=date.today(), age_months=obs_age,
                source="dialog", confidence=confidence
            )
            db.add(obs)
            new_obs_models.append(obs)
            updated_domains.add(domain)
            # Check red flags against milestones
            m_r = await db.execute(select(Milestone).where(Milestone.code == milestone_code))
            m = m_r.scalar_one_or_none()
            if m and status == "not_yet" and m.age_months_concern and obs_age > m.age_months_concern:
                red_flags.append(f"{domain}: {m.title}")
                db.add(DevelopmentRecommendation(
                    child_id=child.id, domain=domain,
                    activity_title=f"Консультация специалиста: {m.title}",
                    activity_description=f"Навык '{m.title}' обычно формируется к {m.age_months_concern} месяцам. Рекомендуем проконсультироваться с педиатром или профильным специалистом.",
                    target_milestone=milestone_code, priority="high", is_red_flag=True,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30)
                ))
        except Exception:
            continue

    await db.flush()

    # Generate AI reply
    red_flag_note = ""
    if red_flags:
        red_flag_note = " Обнаружены красные флаги: " + ", ".join(red_flags) + ". Пожалуйста, обратитесь к специалисту."

    system_reply = (
        "You are a warm, supportive AI parenting assistant. "
        "Respond in Russian. Be concise (2-4 sentences). "
        "Acknowledge what the parent shared, add one helpful insight or tip about the developmental stage."
    )
    context = f"Child: {age} months old. Parent message: {message}"
    if observations_extracted:
        context += f"\nObservations detected: {len(observations_extracted)}"
    reply_text = await _claude(system_reply, context)
    if not reply_text:
        reply_text = f"Спасибо за информацию о развитии вашего ребёнка ({age} мес.)! Продолжайте наблюдать и записывать успехи."
    if red_flag_note:
        reply_text += red_flag_note

    # Save assistant message
    db.add(DialogMessage(child_id=child.id, role="assistant", content=reply_text,
                         extracted_observations=[vars(o) for o in extracted]))
    await db.commit()
    for obs in new_obs_models:
        await db.refresh(obs)

    return DialogResponse(
        reply=reply_text,
        updated_domains=list(updated_domains),
        new_observations=[ObservationResponse.model_validate(o) for o in new_obs_models],
        red_flags=red_flags
    )

async def generate_recommendations(child: Child, db: AsyncSession) -> list:
    age = _age_months(child.birth_date)
    domains = ["speech", "motor_fine", "motor_gross", "cognitive", "social", "emotional"]
    recs = []
    # Expire old recommendations
    from sqlalchemy import update
    await db.execute(
        update(DevelopmentRecommendation)
        .where(DevelopmentRecommendation.child_id == child.id, DevelopmentRecommendation.is_red_flag == False)
        .values(expires_at=datetime.now(timezone.utc))
    )
    for domain in domains:
        # Find next milestones (current age to age+4 months)
        m_r = await db.execute(
            select(Milestone).where(
                Milestone.domain == domain,
                Milestone.age_months_min >= age,
                Milestone.age_months_min <= age + 4
            ).limit(3)
        )
        milestones = m_r.scalars().all()
        if not milestones:
            continue
        ms_titles = ", ".join(m.title for m in milestones)
        system = (
            "You are a child development expert. Suggest 1-2 practical activities for the parent. "
            "Respond in Russian. Return JSON array: [{\"title\": str, \"description\": str, \"priority\": low/medium/high}]. JSON only."
        )
        prompt = f"Child: {age} months. Domain: {domain}. Next milestones: {ms_titles}"
        raw = await _claude(system, prompt)
        try:
            activities = json.loads(raw) if raw else []
        except Exception:
            activities = []
        for act in activities[:2]:
            rec = DevelopmentRecommendation(
                child_id=child.id, domain=domain,
                activity_title=act.get("title", f"Активность для {domain}"),
                activity_description=act.get("description", ""),
                target_milestone=milestones[0].code if milestones else None,
                priority=act.get("priority", "medium"),
                is_red_flag=False,
                expires_at=datetime.now(timezone.utc) + timedelta(days=14)
            )
            db.add(rec)
            recs.append(rec)
    await db.commit()
    for r in recs:
        await db.refresh(r)
    return recs
