from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database.session import get_db
from app.models.activity import Feedback, Prediction, SyncLog
from app.models.catalog import Disease
from app.models.user import User
from app.schemas.activity import (
    FeedbackInput,
    FeedbackRead,
    PredictionRead,
    PredictionSyncRequest,
    PredictionSyncResponse,
    SyncItemResponse,
)

router = APIRouter(prefix="/api", tags=["Research records"])


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _same_record(existing: Prediction, incoming: object) -> bool:
    return (
        existing.crop == incoming.crop
        and existing.model_class_id == incoming.model_class_id
        and existing.confidence == incoming.confidence
        and existing.is_below_threshold == incoming.is_below_threshold
        and existing.model_version == incoming.model_version
        and _utc(existing.captured_at) == _utc(incoming.captured_at)
    )


@router.post("/predictions/sync", response_model=PredictionSyncResponse)
def sync_predictions(
    request: PredictionSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PredictionSyncResponse:
    results: list[SyncItemResponse] = []
    accepted = 0
    conflicted = 0
    for incoming in request.records:
        existing = db.scalar(
            select(Prediction).where(
                Prediction.user_id == user.id, Prediction.local_id == incoming.local_id
            )
        )
        if existing is not None:
            if _same_record(existing, incoming):
                accepted += 1
                results.append(
                    SyncItemResponse(local_id=incoming.local_id, status="SYNCED", server_id=existing.id)
                )
            else:
                conflicted += 1
                results.append(SyncItemResponse(local_id=incoming.local_id, status="CONFLICT"))
            continue

        disease_id = db.scalar(
            select(Disease.id).where(Disease.model_class_id == incoming.model_class_id)
        )
        prediction = Prediction(
            user_id=user.id,
            local_id=incoming.local_id,
            crop=incoming.crop,
            model_class_id=incoming.model_class_id,
            disease_id=disease_id,
            confidence=incoming.confidence,
            is_below_threshold=incoming.is_below_threshold,
            model_version=incoming.model_version,
            captured_at=_utc(incoming.captured_at),
        )
        db.add(prediction)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.scalar(
                select(Prediction).where(
                    Prediction.user_id == user.id, Prediction.local_id == incoming.local_id
                )
            )
            if existing is not None and _same_record(existing, incoming):
                accepted += 1
                results.append(
                    SyncItemResponse(local_id=incoming.local_id, status="SYNCED", server_id=existing.id)
                )
            else:
                conflicted += 1
                results.append(SyncItemResponse(local_id=incoming.local_id, status="CONFLICT"))
            continue
        db.refresh(prediction)
        accepted += 1
        results.append(
            SyncItemResponse(local_id=incoming.local_id, status="SYNCED", server_id=prediction.id)
        )

    db.add(
        SyncLog(user_id=user.id, attempted=len(request.records), accepted=accepted, conflicted=conflicted)
    )
    db.commit()
    return PredictionSyncResponse(results=results)


@router.get("/predictions", response_model=list[PredictionRead])
def list_predictions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Prediction]:
    return list(
        db.scalars(
            select(Prediction)
            .where(Prediction.user_id == user.id)
            .order_by(Prediction.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )


@router.get("/predictions/{prediction_id}", response_model=PredictionRead)
def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Prediction:
    prediction = db.get(Prediction, prediction_id)
    if prediction is None or (prediction.user_id != user.id and user.role.name != "admin"):
        raise HTTPException(status_code=404, detail="Prediction not found")
    return prediction


@router.post("/feedback", response_model=FeedbackRead, status_code=201)
def create_feedback(
    data: FeedbackInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Feedback:
    if data.prediction_id is not None:
        prediction = db.get(Prediction, data.prediction_id)
        if prediction is None or prediction.user_id != user.id:
            raise HTTPException(status_code=404, detail="Prediction not found")
    feedback = Feedback(user_id=user.id, prediction_id=data.prediction_id, message=data.message)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/feedback", response_model=list[FeedbackRead])
def list_feedback(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None, pattern="^(OPEN|RESOLVED)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[Feedback]:
    query = select(Feedback).order_by(Feedback.id.desc()).offset(offset).limit(limit)
    if status is not None:
        query = query.where(Feedback.status == status)
    return list(db.scalars(query))


@router.put("/feedback/{feedback_id}/resolve", response_model=FeedbackRead)
def resolve_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Feedback:
    feedback = db.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    feedback.status = "RESOLVED"
    db.commit()
    db.refresh(feedback)
    return feedback
