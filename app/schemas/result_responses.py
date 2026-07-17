from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ==========================================================
# INPUTS
# ==========================================================


class SubjectScoreInput(BaseModel):
    subject_id: UUID
    ca_score: int = Field(ge=0, le=40)
    exam_score: int = Field(ge=0, le=60)
    teacher_comment: str | None = None


class StudentResultInput(BaseModel):
    student_id: UUID
    scores: list[SubjectScoreInput]


class ResultBatchCreate(BaseModel):
    class_id: UUID
    students: list[StudentResultInput]


# ==========================================================
# UPDATE RESULT
# ==========================================================


class UpdateResultRecordRequest(BaseModel):
    ca_score: int = Field(ge=0, le=40)
    exam_score: int = Field(ge=0, le=60)
    teacher_comment: str | None = None


class UpdateTeacherComment(BaseModel):
    teacher_comment: str


# ==========================================================
# SUBJECT RESPONSE
# ==========================================================


class SubjectResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    record_id: UUID

    subject_id: UUID
    subject_name: str

    ca_score: int
    exam_score: int

    total_score: int

    grade: str
    remark: str | None

    teacher_comment: str | None


# ==========================================================
# CLASS STUDENT RESPONSE
# ==========================================================


class ClassSubjectResponse(BaseModel):
    subject_id: UUID
    subject_name: str


class ClassStudentResponse(BaseModel):
    student_id: UUID

    student_name: str

    total_score: int

    average_score: float

    position: int | None

    passed_subjects: int

    failed_subjects: int

    subjects: list[SubjectResultResponse]


# ==========================================================
# CLASS RESULT RESPONSE
# ==========================================================


class ClassResultResponse(BaseModel):
    batch_id: UUID | None = None

    class_id: UUID
    session_id: UUID
    term_id: UUID

    status: str
    editable: bool

    subjects: list[ClassSubjectResponse]

    students: list[ClassStudentResponse]


# ==========================================================
# SUBMISSION RESPONSE
# ==========================================================


class ResultSubmissionResponse(BaseModel):
    created: bool

    batch_id: UUID

    status: str

    message: str


# ==========================================================
# BATCH STATUS
# ==========================================================


class ResultBatchStatusResponse(BaseModel):
    batch_id: UUID

    status: str

    message: str


# ==========================================================
# APPROVAL HISTORY
# ==========================================================


class ApprovalHistoryItem(BaseModel):
    id: UUID

    action: str

    note: str | None

    action_by: UUID

    action_at: datetime


# ==========================================================
# STUDENT PORTAL RESPONSE
# ==========================================================


class StudentResultResponse(BaseModel):
    student_id: UUID

    student_name: str

    class_name: str

    session_name: str

    term_name: str

    total_score: int

    average_score: float

    position: int | None

    passed_subjects: int

    failed_subjects: int

    subjects: list[SubjectResultResponse]


class StudentResultData(BaseModel):
    student_id: UUID
    student_name: str
    class_name: str
    session_name: str
    term_name: str

    total_score: int
    average_score: float
    position: int | None

    passed_subjects: int
    failed_subjects: int

    subjects: list[SubjectResultResponse]


class StudentResultApiResponse(BaseModel):
    published: bool
    message: str
    data: StudentResultResponse | None = None
