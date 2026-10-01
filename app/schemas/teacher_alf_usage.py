from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums.alf import ALFSessionStatus


class ALFUsageSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    teacher_id: UUID
    teacher_name: str

    lesson_id: UUID
    lesson_title: str
    subject_name: str

    class_id: UUID
    class_name: str

    started_at: datetime
    last_activity_at: datetime
    completed_at: datetime | None = None

    duration_seconds: int = Field(ge=0)

    status: ALFSessionStatus

    independent_reading_completed: bool
    mini_lesson_completed: bool
    case_study_completed: bool
    project_based_learning_completed: bool
    evaluation_completed: bool

    progress_percentage: int = Field(ge=0, le=100)


class ALFUsageStatsResponse(BaseModel):
    total_sessions: int
    completed_sessions: int
    in_progress_sessions: int
    started_sessions: int
    abandoned_sessions: int

    total_duration_seconds: int
    average_duration_seconds: int

    completion_rate: float = Field(ge=0, le=100)


class ALFLessonUsageResponse(BaseModel):
    lesson_id: UUID
    lesson_title: str
    subject_name: str

    total_sessions: int
    completed_sessions: int
    active_sessions: int

    total_duration_seconds: int
    average_duration_seconds: int

    completion_rate: float = Field(ge=0, le=100)


class ALFTeacherUsageResponse(BaseModel):
    teacher_id: UUID
    teacher_name: str

    total_sessions: int
    completed_sessions: int
    active_sessions: int

    total_duration_seconds: int
    average_duration_seconds: int

    completion_rate: float = Field(ge=0, le=100)
