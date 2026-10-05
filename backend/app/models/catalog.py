from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.user import utc_now


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    diseases: Mapped[list["Disease"]] = relationship(back_populates="crop")


class Disease(Base):
    __tablename__ = "diseases"
    __table_args__ = (
        UniqueConstraint("crop_id", "name", name="uq_diseases_crop_name"),
        UniqueConstraint("model_class_id", name="uq_diseases_model_class_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    model_class_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    crop: Mapped[Crop] = relationship(back_populates="diseases")
    treatment: Mapped["Treatment | None"] = relationship(back_populates="disease", uselist=False)


class Treatment(Base):
    __tablename__ = "treatments"
    __table_args__ = (
        CheckConstraint("review_status IN ('DRAFT', 'APPROVED')", name="ck_treatment_review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("diseases.id"), unique=True, nullable=False, index=True
    )
    prevention: Mapped[str] = mapped_column(Text, nullable=False)
    care_guidance: Mapped[str] = mapped_column(Text, nullable=False)
    safety_precautions: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    disease: Mapped[Disease] = relationship(back_populates="treatment")
