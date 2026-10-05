from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database.session import get_db
from app.models.activity import Prediction
from app.models.catalog import Crop, Disease
from app.models.user import User
from app.schemas.activity import PredictionRead
from app.schemas.admin import AdminStatistics, TrendPoint, UserActiveUpdate, UserAdminRead

router = APIRouter(prefix="/api/admin", tags=["Administration"])


def user_read(user: User) -> UserAdminRead:
    return UserAdminRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/statistics", response_model=AdminStatistics)
def statistics(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> AdminStatistics:
    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=6)
    grouped = db.execute(
        select(func.date(Prediction.created_at), func.count(Prediction.id))
        .where(Prediction.created_at >= datetime.combine(first_day, datetime.min.time(), timezone.utc))
        .group_by(func.date(Prediction.created_at))
    ).all()
    counts = {str(day): count for day, count in grouped}
    trend = [
        TrendPoint(date=str(first_day + timedelta(days=offset)), count=counts.get(str(first_day + timedelta(days=offset)), 0))
        for offset in range(7)
    ]
    recent = list(db.scalars(select(Prediction).order_by(Prediction.id.desc()).limit(10)))
    return AdminStatistics(
        total_users=db.scalar(select(func.count(User.id))) or 0,
        total_predictions=db.scalar(select(func.count(Prediction.id))) or 0,
        total_diseases=db.scalar(select(func.count(Disease.id))) or 0,
        total_crops=db.scalar(select(func.count(Crop.id))) or 0,
        recent_predictions=[PredictionRead.model_validate(item) for item in recent],
        prediction_trend=trend,
    )


@router.get("/users", response_model=list[UserAdminRead])
def list_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[UserAdminRead]:
    return [user_read(user) for user in db.scalars(select(User).order_by(User.id).offset(offset).limit(limit))]


@router.put("/users/{user_id}/active", response_model=UserAdminRead)
def set_user_active(
    user_id: int,
    data: UserActiveUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserAdminRead:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id and not data.is_active:
        raise HTTPException(status_code=409, detail="Cannot deactivate your own account")
    target.is_active = data.is_active
    db.commit()
    db.refresh(target)
    return user_read(target)


@router.get("/predictions", response_model=list[PredictionRead])
def list_all_predictions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[Prediction]:
    return list(db.scalars(select(Prediction).order_by(Prediction.id.desc()).offset(offset).limit(limit)))
