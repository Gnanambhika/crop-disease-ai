from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.user import utc_now


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "local_id", name="uq_prediction_user_local"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_prediction_confidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    local_id: Mapped[str] = mapped_column(String(80), nullable=False)
    crop: Mapped[str] = mapped_column(String(100), nullable=False)
    model_class_id: Mapped[str] = mapped_column(String(200), nullable=False)
    disease_id: Mapped[int | None] = mapped_column(
        ForeignKey("diseases.id"), nullable=True, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    is_below_threshold: Mapped[bool] = mapped_column(Boolean, nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user = relationship("User")
    disease = relationship("Disease")


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="ck_feedback_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    prediction_id: Mapped[int | None] = mapped_column(
        ForeignKey("predictions.id"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SyncLog(Base):
    __tablename__ = "sync_logs"
    __table_args__ = (
        CheckConstraint("attempted >= 0 AND accepted >= 0 AND conflicted >= 0", name="ck_sync_counts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted: Mapped[int] = mapped_column(Integer, nullable=False)
    conflicted: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
