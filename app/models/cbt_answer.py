from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
)


class CBTAnswer(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "cbt_answers"

    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "cbt_attempts.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    question_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "cbt_questions.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    selected_option_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "cbt_question_options.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    marks_awarded: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    # -------------------------
    # Relationships
    # -------------------------

    attempt = relationship(
        "CBTAttempt",
        back_populates="answers",
    )

    question = relationship(
        "CBTQuestion",
        back_populates="answers",
    )

    selected_option = relationship(
        "CBTQuestionOption",
        back_populates="answers",
    )

    __table_args__ = (
        Index(
            "ix_attempt_question",
            "attempt_id",
            "question_id",
            unique=True,
        ),
    )
