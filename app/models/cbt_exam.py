from enum import Enum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
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


class AssessmentType(str, Enum):
    CA = "CA"
    EXAM = "EXAM"


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

    assessment_type: Mapped[AssessmentType] = mapped_column(
        SQLEnum(AssessmentType, name="cbt_assessment_type"),
        nullable=False,
        default=AssessmentType.CA,
    )

    assessment_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    assessment_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Assessment",
    )

    contribution_marks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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
    is_result_assessment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    attempts = relationship(
        "CBTAttempt",
        back_populates="exam",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "(assessment_type = 'CA' AND assessment_number IS NOT NULL AND contribution_marks BETWEEN 1 AND 40) "
            "OR (assessment_type = 'EXAM' AND assessment_number IS NULL AND contribution_marks = 60)",
            name="ck_cbt_exam_assessment_allocation",
        ),
        CheckConstraint("max_attempts >= 1", name="ck_cbt_exam_max_attempts_positive"),
        Index(
            "uq_cbt_ca_assessment_number",
            "school_id",
            "session_id",
            "term_id",
            "class_id",
            "subject_id",
            "assessment_number",
            unique=True,
            postgresql_where=text("assessment_type = 'CA'"),
        ),
        Index(
            "uq_cbt_main_exam",
            "school_id",
            "session_id",
            "term_id",
            "class_id",
            "subject_id",
            unique=True,
            postgresql_where=text("assessment_type = 'EXAM'"),
        ),
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
