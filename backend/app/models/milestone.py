import uuid
from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Milestone(Base):
    __tablename__ = "milestones"
    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_months_min: Mapped[int] = mapped_column(Integer, nullable=False)
    age_months_max: Mapped[int] = mapped_column(Integer, nullable=False)
    age_months_concern: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="WHO")
