from enum import Enum
from uuid import UUID

from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
)


class QuestionType(str, Enum):
    OBJECTIVE = "OBJECTIVE"
    TRUE_FALSE = "TRUE_FALSE"


class CBTQuestion(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "cbt_questions"

    exam_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "cbt_exams.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    question: Mapped[str] = mapped_column(
        Text,
    )

    type: Mapped[QuestionType] = mapped_column(
        SQLEnum(QuestionType),
        default=QuestionType.OBJECTIVE,
    )

    marks: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    question_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ----------------------------
    # Relationships
    # ----------------------------

    exam = relationship(
        "CBTExam",
        back_populates="questions",
    )

    options = relationship(
        "CBTQuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    answers = relationship(
        "CBTAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_exam_question_order",
            "exam_id",
            "question_order",
        ),
    )
