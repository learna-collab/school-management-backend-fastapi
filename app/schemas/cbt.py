from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

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

    starts_at: datetime | None = None

    ends_at: datetime | None = None


class SubmitAnswerRequest(BaseModel):
    attempt_id: UUID

    question_id: UUID

    option_id: UUID


class SubmitExamRequest(BaseModel):
    attempt_id: UUID


# ===========================================================
# DASHBOARD RESPONSES
# ===========================================================


class CBTResultsDashboardStats(BaseModel):
    total_exams: int

    total_attempts: int

    average_percentage: float

    overall_pass_rate: float


class CBTResultsDashboardItem(BaseModel):
    exam_id: UUID

    title: str

    class_name: str

    subject_name: str

    attempts: int

    average_score: float

    average_percentage: float

    highest_score: int

    lowest_score: int

    pass_rate: float

    total_marks: int

    published: bool

    starts_at: datetime | None

    ends_at: datetime | None


class CBTResultsDashboardResponse(BaseModel):
    results: list[CBTResultsDashboardItem]

    count: int

    stats: CBTResultsDashboardStats


# ===========================================================
# ADMIN QUESTION RESPONSES
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

    # ADMIN ONLY
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


# ===========================================================
# EXAM RESPONSES (ADMIN)
# ===========================================================


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

    school_class: ClassMiniResponse | None = None

    subject: SubjectMiniResponse | None = None

    questions: list[QuestionResponse] = Field(default_factory=list)


# ===========================================================
# ATTEMPTS
# ===========================================================


class StudentSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    first_name: str

    last_name: str

    email: str | None = None

    admission_number: str | None = None

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class AttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    exam_id: UUID

    student_id: UUID

    student: StudentSummaryResponse | None = None

    started_at: datetime

    submitted_at: datetime | None

    score: int

    percentage: float

    is_passed: bool


class ExamSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    title: str

    duration_minutes: int

    total_marks: int

    starts_at: datetime

    ends_at: datetime

    is_published: bool

    question_count: int

    class_name: str

    subject_name: str


class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    attempt_id: UUID

    question_id: UUID

    selected_option_id: UUID


# ===========================================================
# STUDENT EXAM FLOW
# ===========================================================


class ExamAttemptStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"

    IN_PROGRESS = "IN_PROGRESS"

    COMPLETED = "COMPLETED"


# NO CORRECT ANSWER HERE


class StudentQuestionOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    option_label: str

    option_text: str

    option_order: int


class StudentQuestionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID

    question_text: str = Field(validation_alias="question")

    marks: int

    order_no: int = Field(validation_alias="question_order")

    selected_option_id: UUID | None = None

    options: list[StudentQuestionOptionResponse]


class StudentExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    title: str

    instructions: str | None = None

    duration_minutes: int

    total_marks: int

    subject_name: str

    class_name: str

    question_count: int

    attempt_status: ExamAttemptStatus

    attempt_id: UUID | None = None


class UpdateQuestionPositionRequest(BaseModel):
    current_question_index: int


class StudentExamAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID
    current_question_index: int

    exam_id: UUID

    title: str

    instructions: str | None

    duration_minutes: int

    total_marks: int

    started_at: datetime
    expires_at: datetime | None

    completed_at: datetime | None = None

    remaining_seconds: int

    questions: list[StudentQuestionResponse]


# ===========================================================
# RESULTS
# ===========================================================


class StudentResultResponse(BaseModel):
    attempt_id: UUID

    exam_id: UUID

    exam_title: str

    subject_name: str

    total_marks: int

    score: int

    percentage: float

    passed: bool

    total_questions: int

    answered_questions: int

    correct_answers: int

    wrong_answers: int

    started_at: datetime

    completed_at: datetime | None


class StudentHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID

    exam_id: UUID

    exam_title: str

    subject_name: str

    score: int

    percentage: float

    passed: bool

    completed_at: datetime | None


class StudentHistoryResponse(BaseModel):
    attempts: list[StudentHistoryItem]

    count: int


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
    exam: ExamSummaryResponse | None = None

    attempts: list[AttemptResponse]

    count: int

    average_score: float = 0

    highest_score: int = 0

    lowest_score: int = 0

    passed_count: int = 0

    failed_count: int = 0


class StudentExamListResponse(BaseModel):
    exams: list[StudentExamResponse]

    count: int


# ===========================================================
# API WRAPPERS
# ===========================================================


class CBTApiResponse(BaseModel):
    success: bool

    message: str


class ExamApiResponse(CBTApiResponse):
    data: ExamResponse | None = None


class QuestionApiResponse(CBTApiResponse):
    data: QuestionResponse | None = None


class AttemptApiResponse(CBTApiResponse):
    data: AttemptResponse | None = None


class AnswerApiResponse(CBTApiResponse):
    data: AnswerResponse | None = None


class CBTResultsDashboardApiResponse(CBTApiResponse):
    data: CBTResultsDashboardResponse | None = None


class ExamListApiResponse(CBTApiResponse):
    data: ExamListResponse | None = None


class QuestionListApiResponse(CBTApiResponse):
    data: QuestionListResponse | None = None


class AttemptListApiResponse(CBTApiResponse):
    data: AttemptListResponse | None = None


class StudentExamListApiResponse(CBTApiResponse):
    data: StudentExamListResponse | None = None


class StudentExamAttemptApiResponse(CBTApiResponse):
    data: StudentExamAttemptResponse | None = None


class StudentResultApiResponse(CBTApiResponse):
    data: StudentResultResponse | None = None


class StudentHistoryApiResponse(CBTApiResponse):
    data: StudentHistoryResponse | None = None


class SuccessApiResponse(CBTApiResponse):
    pass


# ===========================================================
# STUDENT SUBMIT EXAM RESPONSE
# ===========================================================


class StudentExamResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID

    exam_id: UUID

    title: str

    score: int

    total_marks: int

    percentage: float

    passed: bool

    answered_questions: int

    total_questions: int

    completed_at: datetime


class StudentExamResultApiResponse(CBTApiResponse):
    data: StudentExamResultResponse | None = None
