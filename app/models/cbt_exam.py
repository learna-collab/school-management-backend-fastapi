from enum import Enum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class ExamStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class CBTExam(
    Base,
    UUIDMixin,
    TenantMixin,
    TimestampMixin,
):
    __tablename__ = "cbt_exams"

    title: Mapped[str] = mapped_column(
        String(255),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_published = mapped_column(Boolean, default=False)

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "academic_sessions.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    term_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "terms.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "classes.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "subjects.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=60,
    )

    total_marks: Mapped[int] = mapped_column(
        Integer,
        default=100,
    )

    pass_mark: Mapped[int] = mapped_column(
        Integer,
        default=40,
    )

    starts_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ends_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[ExamStatus] = mapped_column(
        SQLEnum(ExamStatus),
        default=ExamStatus.DRAFT,
    )

    published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    shuffle_questions: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    shuffle_options: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    allow_review: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    show_result_immediately: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -------------------------
    # Relationships
    # -------------------------

    school_class = relationship(
        "Class",
        back_populates="cbt_exams",
    )

    subject = relationship(
        "Subject",
        back_populates="cbt_exams",
    )

    session = relationship(
        "AcademicSession",
        back_populates="cbt_exams",
    )

    term = relationship(
        "Term",
        back_populates="cbt_exams",
    )

    questions = relationship(
        "CBTQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
    )

    attempts = relationship(
        "CBTAttempt",
        back_populates="exam",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_cbt_exam_class_subject",
            "class_id",
            "subject_id",
        ),
        Index(
            "ix_cbt_exam_session_term",
            "session_id",
            "term_id",
        ),
    )
