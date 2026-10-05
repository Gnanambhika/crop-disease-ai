from pydantic import BaseModel, ConfigDict, Field, field_validator


class CropInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must have at least two visible characters")
        return value


class CropRead(CropInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DiseaseInput(BaseModel):
    crop_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=150)
    model_class_id: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=5)
    symptoms: str = Field(min_length=5)

    @field_validator("name", "description", "symptoms")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Text cannot be blank")
        return value

    @field_validator("model_class_id")
    @classmethod
    def clean_model_class_id(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class DiseaseRead(DiseaseInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TreatmentInput(BaseModel):
    disease_id: int = Field(gt=0)
    prevention: str = Field(min_length=5)
    care_guidance: str = Field(min_length=5)
    safety_precautions: str = Field(min_length=5)
    source_reference: str = Field(min_length=5)

    @field_validator("prevention", "care_guidance", "safety_precautions", "source_reference")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Text must have at least five visible characters")
        return value


class TreatmentRead(TreatmentInput):
    id: int
    review_status: str
    model_config = ConfigDict(from_attributes=True)
