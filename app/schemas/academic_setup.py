from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.classes import AcademicLevel

# ==========================================================
# TEMPLATE RESPONSE
# ==========================================================


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


# ==========================================================
# CONFIGURE SETUP REQUEST
# ==========================================================


class ConfigureSubjectRequest(BaseModel):
    """
    If template_subject_id is provided,
    clone from template.

    Otherwise create a custom subject.
    """

    template_subject_id: UUID | None = None

    name: str = Field(min_length=1, max_length=100)

    code: str | None = Field(default=None, max_length=20)

    enabled: bool = True

    is_custom: bool = False


class ConfigureClassRequest(BaseModel):
    """
    If template_class_id is provided,
    clone from template.

    Otherwise create a custom class.
    """

    template_class_id: UUID | None = None

    name: str = Field(min_length=1, max_length=100)

    level: AcademicLevel

    sort_order: int = 0

    enabled: bool = True

    is_custom: bool = False

    subjects: list[ConfigureSubjectRequest] = Field(default_factory=list)


class ConfigureAcademicSetupRequest(BaseModel):
    academic_template_id: UUID

    classes: list[ConfigureClassRequest] = Field(min_length=1)


# ==========================================================
# SCHOOL SETUP RESPONSE
# ==========================================================


class SchoolSubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    template_subject_id: UUID | None = None

    name: str

    code: str | None = None

    is_custom: bool = False


class SchoolClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    template_class_id: UUID | None = None

    name: str

    level: AcademicLevel | str = ""

    sort_order: int | None = None

    is_custom: bool = False

    subjects: list[SchoolSubjectResponse]


class SchoolAcademicSetupResponse(BaseModel):
    configured: bool

    classes: list[SchoolClassResponse]


# ==========================================================
# CONFIGURE RESPONSE
# ==========================================================


class AcademicSetupSummaryResponse(BaseModel):
    classes_created: int

    subjects_created: int

    mappings_created: int

    message: str

    setup: SchoolAcademicSetupResponse


# ==========================================================
# CLASS CRUD
# ==========================================================


class CreateClassRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    level: AcademicLevel

    sort_order: int = 0


class UpdateClassRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    level: AcademicLevel | None = None

    sort_order: int | None = None


# ==========================================================
# SUBJECT CRUD
# ==========================================================


class CreateSubjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    code: str | None = Field(default=None, max_length=20)


class UpdateSubjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    code: str | None = Field(default=None, max_length=20)


# ==========================================================
# CLASS SUBJECT ASSIGNMENT
# ==========================================================


class AssignSubjectsRequest(BaseModel):
    subject_ids: list[UUID] = Field(min_length=1)
