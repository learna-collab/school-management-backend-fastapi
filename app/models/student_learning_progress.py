from uuid import UUID as PyUUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class StudentLearningProgress(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "student_learning_progress"

    __table_args__ = (
        UniqueConstraint(
            "learning_content_id",
            "student_id",
            name="uq_student_learning_progress_content_student",
        ),
        CheckConstraint(
            "attempts_count >= 0",
            name="attempts_nonnegative",
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="score_range",
        ),
        CheckConstraint(
            "status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')",
            name="valid_status",
        ),
    )

    learning_content_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "lesson_learning_contents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    student_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    school_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NOT_STARTED",
        server_default="NOT_STARTED",
        index=True,
    )

    attempts_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    activity_progress: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    learning_content = relationship(
        "LessonLearningContent",
        back_populates="student_progress",
    )

    student = relationship("User")
    school = relationship("School")
