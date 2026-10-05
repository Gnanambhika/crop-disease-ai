"""Idempotent model-class catalog seed; never creates agricultural advice."""
import json
from pathlib import Path
from sqlalchemy import select

from app.database.session import get_session_factory
from app.models.user import Role
from app.models.catalog import Crop, Disease


def model_labels() -> list[str]:
    packaged = Path(__file__).resolve().parents[1] / 'data/model_labels.json'
    source = Path(__file__).resolve().parents[3] / 'mobile/assets/model/labels.json'
    labels = json.loads((packaged if packaged.is_file() else source).read_text())
    if not isinstance(labels, list) or not labels or len(set(labels)) != len(labels):
        raise ValueError('Model labels must be a nonempty unique list')
    if any(not isinstance(label, str) or label.count('__') != 1 for label in labels):
        raise ValueError('Model class identifiers are invalid')
    return labels


def seed(db, labels: list[str]) -> None:
    for name in ("farmer", "admin"):
        if db.scalar(select(Role.id).where(Role.name == name)) is None:
            db.add(Role(name=name))
    for label in labels:
        crop_key, condition = label.split('__')
        name = crop_key.replace('_', ' ').title()
        crop = db.scalar(select(Crop).where(Crop.name == name))
        if crop is None:
            crop = Crop(name=name)
            db.add(crop)
            db.flush()
        existing = db.scalar(select(Disease.id).where(Disease.model_class_id == label))
        if existing is not None:
            continue  # Preserve administrator edits, descriptions and reviews.
        condition_name = condition.replace('_', ' ').title()
        if db.scalar(select(Disease.id).where(Disease.crop_id == crop.id, Disease.name == condition_name)) is not None:
            raise ValueError(f'Existing catalog name requires manual class mapping: {label}')
        db.add(Disease(crop_id=crop.id, name=condition_name, model_class_id=label,
                       description=f'Research model category: {label}. This catalog mapping does not establish diagnosis accuracy.',
                       symptoms='Source-reviewed symptoms have not been published. Consult an agricultural expert.'))
        db.flush()
    db.commit()


def main() -> None:
    import os
    if not os.environ.get('DATABASE_URL') and os.environ.get('POSTGRES_HOST'):
        from app.utils.container_start import configure_database
        configure_database()
    labels = model_labels()
    with get_session_factory()() as db:
        seed(db, labels)
    print(f'Research roles and {len(labels)} model class mappings seeded; no treatment advice published.')


if __name__ == "__main__":
    main()
