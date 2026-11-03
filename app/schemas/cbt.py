from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)

from app.models.cbt_exam import AssessmentType

# ===========================================================
# REQUEST SCHEMAS
# ===========================================================


class QuestionOptionCreate(BaseModel):
    option_text: str = Field(..., min_length=1)
    is_correct: bool = False


class QuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1)
    marks: int = Field(default=1, gt=0)
    order_no: int = Field(..., ge=1)

    options: list[QuestionOptionCreate] = Field(
        ...,
        min_length=2,
    )


class CBTExamCreate(BaseModel):
    class_id: UUID
    subject_id: UUID

    title: str = Field(..., min_length=1)
    instructions: str | None = None

    duration_minutes: int = Field(..., gt=0)
    total_marks: int = Field(..., gt=0)

    assessment_type: AssessmentType
    assessment_number: int | None = Field(default=None, gt=0)

    assessment_label: str = Field(
        default="Assessment",
        min_length=1,
        max_length=100,
    )

    contribution_marks: int = Field(..., gt=0)
    max_attempts: int = Field(default=1, ge=1)

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def validate_assessment_allocation(self):
        if self.assessment_type == AssessmentType.CA:
            if self.assessment_number not in (1, 2):
                raise ValueError("Only CA1 and CA2 are allowed.")

            if self.contribution_marks != 20:
                raise ValueError(
                    "Each continuous assessment must contribute exactly 20 marks."
                )

            self.assessment_label = f"CA{self.assessment_number}"

        elif self.assessment_type == AssessmentType.EXAM:
            if self.assessment_number is not None:
                raise ValueError(
                    "The main examination cannot have an assessment number."
                )

            if self.contribution_marks != 60:
                raise ValueError(
                    "The main examination must contribute exactly 60 marks."
                )

            self.assessment_label = "Main Examination"

        return self


class SubmitAnswerRequest(BaseModel):
    attempt_id: UUID
    question_id: UUID
    option_id: UUID


class SubmitExamRequest(BaseModel):
    attempt_id: UUID


class UpdateQuestionPositionRequest(BaseModel):
    current_question_index: int = Field(..., ge=0)


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

    highest_score: float
    lowest_score: float

    pass_rate: float
    total_marks: int

    published: bool

    starts_at: datetime | None = None
    ends_at: datetime | None = None


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

    question_text: str = Field(
        validation_alias="question",
    )

    marks: int

    order_no: int = Field(
        validation_alias="question_order",
    )

    options: list[QuestionOptionResponse] = Field(
        default_factory=list,
    )


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

    assessment_type: AssessmentType
    assessment_number: int | None = None
    assessment_label: str
    contribution_marks: int

    max_attempts: int

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    is_published: bool

    school_class: ClassMiniResponse | None = None
    subject: SubjectMiniResponse | None = None

    questions: list[QuestionResponse] = Field(
        default_factory=list,
    )


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
    submitted_at: datetime | None = None

    score: int
    contribution_score: float = 0

    attempt_number: int = 1

    percentage: float
    is_passed: bool


class ExamSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    title: str

    duration_minutes: int
    total_marks: int

    starts_at: datetime | None = None
    ends_at: datetime | None = None

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


# Student must never receive correct-answer information.


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

    question_text: str = Field(
        validation_alias="question",
    )

    marks: int

    order_no: int = Field(
        validation_alias="question_order",
    )

    selected_option_id: UUID | None = None

    options: list[StudentQuestionOptionResponse] = Field(
        default_factory=list,
    )


class StudentExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    title: str
    instructions: str | None = None

    duration_minutes: int
    total_marks: int

    # Assessment information
    assessment_type: AssessmentType
    assessment_number: int | None = None
    assessment_label: str
    contribution_marks: int

    # Attempt information
    max_attempts: int
    attempt_number: int | None = None
    attempts_used: int = 0
    attempts_remaining: int = 0

    subject_name: str
    class_name: str

    question_count: int

    attempt_status: ExamAttemptStatus
    attempt_id: UUID | None = None


class StudentExamAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID
    current_question_index: int

    exam_id: UUID

    title: str
    instructions: str | None = None

    duration_minutes: int
    total_marks: int

    # Assessment information
    assessment_type: AssessmentType
    assessment_number: int | None = None
    assessment_label: str
    contribution_marks: int

    # Attempt information
    attempt_number: int
    max_attempts: int

    started_at: datetime
    expires_at: datetime | None = None

    completed_at: datetime | None = None

    remaining_seconds: int

    questions: list[StudentQuestionResponse] = Field(
        default_factory=list,
    )


# ===========================================================
# STUDENT RESULTS
# ===========================================================


class StudentResultResponse(BaseModel):
    attempt_id: UUID
    exam_id: UUID

    exam_title: str
    subject_name: str

    total_marks: int
    score: int

    contribution_score: float = 0
    attempt_number: int = 1

    percentage: float
    passed: bool

    total_questions: int
    answered_questions: int

    correct_answers: int
    wrong_answers: int

    started_at: datetime
    completed_at: datetime | None = None


class StudentHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID
    exam_id: UUID

    exam_title: str
    subject_name: str

    score: int

    contribution_score: float = 0
    attempt_number: int = 1

    percentage: float
    passed: bool

    completed_at: datetime | None = None


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

    contribution_score: float = 0
    attempt_number: int = 1

    percentage: float
    passed: bool

    answered_questions: int
    correct_answers: int
    wrong_answers: int
    unanswered_questions: int

    total_questions: int

    completed_at: datetime


class StudentExamResultApiResponse(CBTApiResponse):
    data: StudentExamResultResponse | None = None
