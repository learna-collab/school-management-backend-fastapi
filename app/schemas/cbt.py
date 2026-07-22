from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ===========================================================
# REQUEST SCHEMAS
# ===========================================================


class QuestionOptionCreate(BaseModel):
    option_text: str = Field(..., min_length=1)
    is_correct: bool = False


class QuestionCreate(BaseModel):
    question_text: str
    marks: int = 1
    order_no: int

    options: list[QuestionOptionCreate]


class CBTExamCreate(BaseModel):
    class_id: UUID
    subject_id: UUID

    title: str
    instructions: str | None = None

    duration_minutes: int
    total_marks: int

    starts_at: datetime
    ends_at: datetime


class SubmitAnswerRequest(BaseModel):
    attempt_id: UUID
    question_id: UUID
    option_id: UUID


class SubmitExamRequest(BaseModel):
    attempt_id: UUID


# ===========================================================
# RESPONSE SCHEMAS
# ===========================================================


class QuestionOptionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID
    option_label: str
    option_text: str
    option_order: int
    is_correct: bool


class QuestionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID

    question_text: str = Field(validation_alias="question")

    marks: int

    order_no: int = Field(validation_alias="question_order")

    options: list[QuestionOptionResponse]


class ClassMiniResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class SubjectMiniResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    class_id: UUID
    subject_id: UUID

    title: str
    instructions: str | None = None

    duration_minutes: int
    total_marks: int

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    is_published: bool

    # loaded relationships
    school_class: ClassMiniResponse | None = None
    subject: SubjectMiniResponse | None = None

    questions: list[QuestionResponse] = Field(default_factory=list)


class AttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    exam_id: UUID
    student_id: UUID

    started_at: datetime
    completed_at: datetime | None

    score: int
    percentage: float
    passed: bool


class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    question_id: UUID
    option_id: UUID


# ===========================================================
# BASE RESPONSE
# ===========================================================


class CBTApiResponse(BaseModel):
    success: bool
    message: str


# ===========================================================
# SINGLE OBJECT RESPONSES
# ===========================================================


class ExamApiResponse(CBTApiResponse):
    data: ExamResponse | None = None


class QuestionApiResponse(CBTApiResponse):
    data: QuestionResponse | None = None


class AttemptApiResponse(CBTApiResponse):
    data: AttemptResponse | None = None


class AnswerApiResponse(CBTApiResponse):
    data: AnswerResponse | None = None


# ===========================================================
# LIST RESPONSES
# ===========================================================


class ExamListResponse(BaseModel):
    exams: list[ExamResponse]
    count: int


class QuestionListResponse(BaseModel):
    questions: list[QuestionResponse]
    count: int


class AttemptListResponse(BaseModel):
    attempts: list[AttemptResponse]
    count: int


class ExamListApiResponse(CBTApiResponse):
    data: ExamListResponse | None = None


class QuestionListApiResponse(CBTApiResponse):
    data: QuestionListResponse | None = None


class AttemptListApiResponse(CBTApiResponse):
    data: AttemptListResponse | None = None


# ===========================================================
# RESULT RESPONSES
# ===========================================================


class ExamResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    exam_id: UUID
    student_id: UUID

    score: int
    percentage: float
    passed: bool

    started_at: datetime
    completed_at: datetime | None


class ExamResultListResponse(BaseModel):
    results: list[ExamResultResponse]
    count: int


class ExamResultApiResponse(CBTApiResponse):
    data: ExamResultResponse | None = None


class ExamResultListApiResponse(CBTApiResponse):
    data: ExamResultListResponse | None = None


# ===========================================================
# STUDENT HISTORY
# ===========================================================


class StudentHistoryResponse(BaseModel):
    attempts: list[AttemptResponse]
    count: int


class StudentHistoryApiResponse(CBTApiResponse):
    data: StudentHistoryResponse | None = None


# ===========================================================
# GENERIC SUCCESS RESPONSE
# ===========================================================


class SuccessApiResponse(CBTApiResponse):
    pass
