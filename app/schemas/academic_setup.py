from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.classes import AcademicLevel


class SubjectTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str | None = None
    level: str


class ClassTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    level: str
    sort_order: int

    subjects: list[SubjectTemplateResponse]


class AcademicTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None

    classes: list[ClassTemplateResponse]


class ConfigureSubjectRequest(BaseModel):
    template_subject_id: UUID
    enabled: bool = True


class ConfigureClassRequest(BaseModel):
    template_class_id: UUID
    enabled: bool = True

    subjects: list[ConfigureSubjectRequest]


class AcademicSetupSummaryResponse(BaseModel):
    classes_created: int
    subjects_created: int
    mappings_created: int
    message: str


class ConfigureAcademicSetupRequest(BaseModel):
    academic_template_id: UUID

    classes: list[ConfigureClassRequest]
