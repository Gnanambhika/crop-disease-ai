from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PredictionSyncItem(BaseModel):
    local_id: str = Field(min_length=1, max_length=80)
    crop: str = Field(min_length=2, max_length=100)
    model_class_id: str = Field(min_length=3, max_length=200)
    confidence: float = Field(ge=0, le=1)
    is_below_threshold: bool
    model_version: str = Field(min_length=1, max_length=80)
    captured_at: datetime

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must include a timezone")
        return value


class PredictionSyncRequest(BaseModel):
    records: list[PredictionSyncItem] = Field(min_length=1, max_length=100)


class SyncItemResponse(BaseModel):
    local_id: str
    status: str
    server_id: int | None = None


class PredictionSyncResponse(BaseModel):
    results: list[SyncItemResponse]


class PredictionRead(BaseModel):
    id: int
    user_id: int
    local_id: str
    crop: str
    model_class_id: str
    disease_id: int | None
    confidence: float
    is_below_threshold: bool
    model_version: str
    captured_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackInput(BaseModel):
    prediction_id: int | None = Field(default=None, gt=0)
    message: str = Field(min_length=5, max_length=2000)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Message must have at least five visible characters")
        return value


class FeedbackRead(FeedbackInput):
    id: int
    user_id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
