from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class AttemptStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AUTO_SUBMITTED = "AUTO_SUBMITTED"


class CBTAttempt(
    Base,
    UUIDMixin,
    TenantMixin,
    TimestampMixin,
):
    __tablename__ = "cbt_attempts"

    exam_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "cbt_exams.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_taken: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    score: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    total_marks: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    percentage: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    status: Mapped[AttemptStatus] = mapped_column(
        SQLEnum(AttemptStatus),
        default=AttemptStatus.NOT_STARTED,
    )

    is_passed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # -----------------------------------
    # Relationships
    # -----------------------------------

    exam = relationship(
        "CBTExam",
        back_populates="attempts",
    )

    student = relationship(
        "User",
    )

    answers = relationship(
        "CBTAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_exam_student_attempt",
            "exam_id",
            "student_id",
        ),
    )
