from datetime import datetime

from pydantic import BaseModel

from app.schemas.activity import PredictionRead


class UserAdminRead(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserActiveUpdate(BaseModel):
    is_active: bool


class TrendPoint(BaseModel):
    date: str
    count: int


class AdminStatistics(BaseModel):
    total_users: int
    total_predictions: int
    total_diseases: int
    total_crops: int
    recent_predictions: list[PredictionRead]
    prediction_trend: list[TrendPoint]
