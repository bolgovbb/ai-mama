import uuid
from datetime import datetime
from sqlalchemy import String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class DevelopmentRecommendation(Base):
    __tablename__ = "development_recommendations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("children.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_title: Mapped[str] = mapped_column(String(300), nullable=False)
    activity_description: Mapped[str] = mapped_column(Text, nullable=False)
    target_milestone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    is_red_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rag_sources: Mapped[list] = mapped_column(JSONB, default=list)
