from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums.alf import ALFSessionStatus


class TeacherALFSession(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "teacher_alf_sessions"

    # =======================================
    # TEACHER
    # =======================================

    teacher_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =======================================
    # LESSON
    # =======================================

    lesson_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "lessons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =======================================
    # ACTUAL SCHOOL CLASS
    # =======================================

    class_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "classes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =======================================
    # SESSION TIMING
    # =======================================

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # =======================================
    # SESSION STATUS
    # =======================================

    status: Mapped[ALFSessionStatus] = mapped_column(
        SQLEnum(
            ALFSessionStatus,
            name="alf_session_status",
        ),
        nullable=False,
        default=ALFSessionStatus.STARTED,
    )

    # =======================================
    # ALF PROGRESS
    # =======================================

    independent_reading_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    mini_lesson_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    case_study_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    project_based_learning_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    evaluation_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # =======================================
    # RELATIONSHIPS
    # =======================================

    teacher = relationship(
        "User",
        back_populates="alf_sessions",
        foreign_keys=[teacher_id],
    )

    lesson = relationship(
        "Lesson",
        back_populates="alf_sessions",
        foreign_keys=[lesson_id],
    )

    school_class = relationship(
        "Class",
        back_populates="alf_sessions",
        foreign_keys=[class_id],
    )
