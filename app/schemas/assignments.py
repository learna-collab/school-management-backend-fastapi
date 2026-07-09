from uuid import UUID

from pydantic import BaseModel, ConfigDict

# =====================================================
# COMMON
# =====================================================


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# =====================================================
# SETUP OPTIONS
# =====================================================


class ClassOption(BaseSchema):
    id: UUID

    name: str

    level: str

    sort_order: int


class SubjectOption(BaseSchema):
    id: UUID

    name: str

    code: str | None = None


class TeacherOption(BaseSchema):
    id: UUID

    first_name: str

    last_name: str

    email: str


# =====================================================
# SETUP RESPONSE
# =====================================================


class AssignmentSetupResponse(BaseModel):
    classes: list[ClassOption]

    subjects: list[SubjectOption]

    teachers: list[TeacherOption]


# =====================================================
# CREATE / UPDATE REQUESTS
# =====================================================


class AssignmentItem(BaseModel):
    subject_id: UUID

    teacher_id: UUID


class CreateClassAssignmentsRequest(BaseModel):
    class_id: UUID

    assignments: list[AssignmentItem]


class UpdateClassAssignmentsRequest(BaseModel):
    assignments: list[AssignmentItem]


# =====================================================
# SUMMARY RESPONSE
# =====================================================


class AssignmentSummaryResponse(BaseModel):
    message: str

    created: int = 0

    updated: int = 0

    skipped: int = 0

    created_subjects: list[str] = []

    updated_subjects: list[str] = []

    skipped_subjects: list[str] = []


# =====================================================
# ASSIGNED TEACHER RESPONSE
# =====================================================


class AssignedTeacher(BaseModel):
    id: UUID

    first_name: str

    last_name: str

    email: str


# =====================================================
# ASSIGNED SUBJECT RESPONSE
# =====================================================


class AssignedSubject(BaseModel):
    assignment_id: UUID

    subject_id: UUID

    subject_name: str

    subject_code: str | None = None

    teacher: AssignedTeacher


# =====================================================
# CLASS ASSIGNMENTS RESPONSE
# =====================================================


class ClassAssignmentResponse(BaseModel):
    class_id: UUID

    class_name: str

    assignments: list[AssignedSubject]
