from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums.alf import ALFSessionStatus


class ALFSessionStartRequest(BaseModel):
    """Request to start an ALF session for a specific class."""

    class_id: UUID


class ALFSessionProgressRequest(BaseModel):
    """Request to update completion status of ALF sections."""

    independent_reading_completed: bool | None = None
    mini_lesson_completed: bool | None = None
    case_study_completed: bool | None = None
    project_based_learning_completed: bool | None = None
    evaluation_completed: bool | None = None


class ALFSessionResponse(BaseModel):
    """Detailed ALF session response."""

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


class ALFSessionHistoryResponse(BaseModel):
    """Compact response for ALF session history and lists."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    lesson_id: UUID
    lesson_title: str
    subject_name: str

    class_id: UUID
    class_name: str

    started_at: datetime
    completed_at: datetime | None = None

    duration_seconds: int = Field(ge=0)
    status: ALFSessionStatus
    progress_percentage: int = Field(ge=0, le=100)


class ALFSessionStatsResponse(BaseModel):
    """Summary statistics for a teacher's ALF usage."""

    total_sessions: int = 0
    completed_sessions: int = 0
    in_progress_sessions: int = 0
    abandoned_sessions: int = 0
    total_duration_seconds: int = 0
    average_duration_seconds: int = 0
    completion_rate: float = Field(default=0.0, ge=0, le=100)
