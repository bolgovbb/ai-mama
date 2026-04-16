from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime
from typing import Optional, Any

class ChildCreate(BaseModel):
    name: Optional[str] = None
    birth_date: date
    gender: Optional[str] = None
    metadata: Optional[dict] = {}

class ChildUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    metadata: Optional[dict] = None

class ChildResponse(BaseModel):
    id: UUID
    agent_id: UUID
    name: Optional[str]
    birth_date: date
    gender: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class ObservationCreate(BaseModel):
    domain: str
    milestone_code: str
    status: str
    observed_at: date
    age_months: int
    notes: Optional[str] = None
    confidence: float = 1.0

class ObservationResponse(BaseModel):
    id: UUID
    child_id: UUID
    domain: str
    milestone_code: str
    status: str
    observed_at: date
    age_months: int
    notes: Optional[str]
    confidence: float
    created_at: datetime
    class Config:
        from_attributes = True

class RecommendationResponse(BaseModel):
    id: UUID
    child_id: UUID
    domain: str
    activity_title: str
    activity_description: str
    target_milestone: Optional[str]
    priority: str
    is_red_flag: bool
    generated_at: datetime
    class Config:
        from_attributes = True

class MilestoneResponse(BaseModel):
    code: str
    domain: str
    title: str
    description: Optional[str]
    age_months_min: int
    age_months_max: int
    age_months_concern: Optional[int]
    source: str
    norm_text: Optional[str] = None
    concern_text: Optional[str] = None
    exercises: Optional[list[dict]] = None
    class Config:
        from_attributes = True

class MapDomain(BaseModel):
    domain: str
    score: float
    achieved: int
    expected: int
    red_flags: int

class DevelopmentMap(BaseModel):
    child_id: UUID
    age_months: int
    domains: list[MapDomain]
    overall_score: float

class DialogRequest(BaseModel):
    message: str

class DialogResponse(BaseModel):
    reply: str
    updated_domains: list[str]
    new_observations: list[ObservationResponse]
    red_flags: list[str]
