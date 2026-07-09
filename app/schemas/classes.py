from uuid import UUID

from pydantic import BaseModel, Field

# ==========================================
# CLASS TEMPLATE
# ==========================================


class ClassTemplate(BaseModel):
    name: str
    level: str
    sort_order: int


# ==========================================
# CLASS CONFIGURATION
# ==========================================


class ConfigureClass(BaseModel):
    name: str

    level: str

    sort_order: int

    subject_ids: list[UUID] = Field(default_factory=list)

    teacher_ids: list[UUID] = Field(default_factory=list)


# ==========================================
# SAVE ALL CLASSES
# ==========================================


class SaveAcademicStructureRequest(BaseModel):
    classes: list[ConfigureClass]


# ==========================================
# RESPONSE
# ==========================================


class ClassResponse(BaseModel):
    id: UUID

    name: str

    level: str

    subjects_count: int

    teachers_count: int

    class Config:
        from_attributes = True


class SubjectItem(BaseModel):
    id: UUID

    name: str

    class Config:
        from_attributes = True


class TeacherItem(BaseModel):
    id: UUID

    first_name: str

    last_name: str

    email: str

    class Config:
        from_attributes = True


class ConfiguredClass(BaseModel):
    id: UUID

    name: str

    level: str

    sort_order: int

    subjects: list[SubjectItem]

    teachers: list[TeacherItem]

    class Config:
        from_attributes = True


class AcademicStructureResponse(BaseModel):
    classes: list[ConfiguredClass]
