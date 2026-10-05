from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database.session import get_db
from app.models.catalog import Crop, Disease, Treatment
from app.models.user import User
from app.schemas.catalog import (
    CropInput,
    CropRead,
    DiseaseInput,
    DiseaseRead,
    TreatmentInput,
    TreatmentRead,
)

router = APIRouter(prefix="/api", tags=["Catalog"])


def commit_or_conflict(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=message) from exc


@router.get("/crops", response_model=list[CropRead])
def list_crops(db: Session = Depends(get_db)) -> list[Crop]:
    return list(db.scalars(select(Crop).order_by(Crop.name)))


@router.post("/crops", response_model=CropRead, status_code=201)
def create_crop(
    data: CropInput, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Crop:
    crop = Crop(name=data.name.strip())
    db.add(crop)
    commit_or_conflict(db, "Crop already exists")
    db.refresh(crop)
    return crop


@router.put("/crops/{crop_id}", response_model=CropRead)
def update_crop(
    crop_id: int, data: CropInput, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Crop:
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    crop.name = data.name.strip()
    commit_or_conflict(db, "Crop name already exists")
    db.refresh(crop)
    return crop


@router.delete("/crops/{crop_id}", status_code=204)
def delete_crop(
    crop_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> None:
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    if db.scalar(select(Disease.id).where(Disease.crop_id == crop_id)) is not None:
        raise HTTPException(status_code=409, detail="Remove linked diseases first")
    db.delete(crop)
    db.commit()


@router.get("/diseases", response_model=list[DiseaseRead])
def list_diseases(crop_id: int | None = None, db: Session = Depends(get_db)) -> list[Disease]:
    query = select(Disease).order_by(Disease.id)
    if crop_id is not None:
        query = query.where(Disease.crop_id == crop_id)
    return list(db.scalars(query))


@router.get("/diseases/{disease_id}", response_model=DiseaseRead)
def get_disease(disease_id: int, db: Session = Depends(get_db)) -> Disease:
    disease = db.get(Disease, disease_id)
    if disease is None:
        raise HTTPException(status_code=404, detail="Disease not found")
    return disease


@router.post("/diseases", response_model=DiseaseRead, status_code=201)
def create_disease(
    data: DiseaseInput, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Disease:
    if db.get(Crop, data.crop_id) is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    disease = Disease(**data.model_dump())
    db.add(disease)
    commit_or_conflict(db, "Disease name or model class already exists")
    db.refresh(disease)
    return disease


@router.put("/diseases/{disease_id}", response_model=DiseaseRead)
def update_disease(
    disease_id: int,
    data: DiseaseInput,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Disease:
    disease = db.get(Disease, disease_id)
    if disease is None:
        raise HTTPException(status_code=404, detail="Disease not found")
    if db.get(Crop, data.crop_id) is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    for key, value in data.model_dump().items():
        setattr(disease, key, value)
    commit_or_conflict(db, "Disease name or model class already exists")
    db.refresh(disease)
    return disease


@router.delete("/diseases/{disease_id}", status_code=204)
def delete_disease(
    disease_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> None:
    disease = db.get(Disease, disease_id)
    if disease is None:
        raise HTTPException(status_code=404, detail="Disease not found")
    if db.scalar(select(Treatment.id).where(Treatment.disease_id == disease_id)) is not None:
        raise HTTPException(status_code=409, detail="Remove linked treatment first")
    db.delete(disease)
    db.commit()


@router.get("/treatments/drafts", response_model=list[TreatmentRead])
def list_draft_treatments(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[Treatment]:
    return list(db.scalars(select(Treatment).where(Treatment.review_status == "DRAFT")))


@router.get("/admin/treatments", response_model=list[TreatmentRead])
def list_admin_treatments(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[Treatment]:
    return list(db.scalars(select(Treatment).order_by(Treatment.id)))


@router.get("/treatments/{disease_id}", response_model=TreatmentRead)
def get_treatment(disease_id: int, db: Session = Depends(get_db)) -> Treatment:
    treatment = db.scalar(
        select(Treatment).where(
            Treatment.disease_id == disease_id,
            Treatment.review_status == "APPROVED",
        )
    )
    if treatment is None:
        raise HTTPException(status_code=404, detail="Reviewed treatment not available")
    return treatment


@router.post("/treatments", response_model=TreatmentRead, status_code=201)
def create_treatment(
    data: TreatmentInput, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Treatment:
    if db.get(Disease, data.disease_id) is None:
        raise HTTPException(status_code=404, detail="Disease not found")
    treatment = Treatment(**data.model_dump(), review_status="DRAFT")
    db.add(treatment)
    commit_or_conflict(db, "A treatment already exists for this disease")
    db.refresh(treatment)
    return treatment


@router.put("/treatments/{treatment_id}", response_model=TreatmentRead)
def update_treatment(
    treatment_id: int,
    data: TreatmentInput,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Treatment:
    treatment = db.get(Treatment, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")
    if db.get(Disease, data.disease_id) is None:
        raise HTTPException(status_code=404, detail="Disease not found")
    for key, value in data.model_dump().items():
        setattr(treatment, key, value)
    treatment.review_status = "DRAFT"
    commit_or_conflict(db, "A treatment already exists for this disease")
    db.refresh(treatment)
    return treatment


@router.delete("/treatments/{treatment_id}", status_code=204)
def delete_treatment(
    treatment_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> None:
    treatment = db.get(Treatment, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")
    db.delete(treatment)
    db.commit()
