import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(ARRAY(String), default=list)
    sources: Mapped[dict | list] = mapped_column(JSONB, default=list)  # list[dict] or dict with rag_metadata
    age_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    factcheck_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    meta_description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    reactions_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    # Moderation
    moderation_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    moderation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent: Mapped["Agent"] = relationship("Agent", lazy="select", foreign_keys=[agent_id])
