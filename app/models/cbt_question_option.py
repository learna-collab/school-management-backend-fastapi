from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
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


class CBTQuestionOption(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "cbt_question_options"

    question_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "cbt_questions.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    option_label: Mapped[str] = mapped_column(
        String(5),
    )

    option_text: Mapped[str] = mapped_column(
        Text,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    option_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    # ------------------------
    # Relationships
    # ------------------------

    question = relationship(
        "CBTQuestion",
        back_populates="options",
    )

    answers = relationship(
        "CBTAnswer",
        back_populates="selected_option",
    )

    __table_args__ = (
        Index(
            "ix_question_option_order",
            "question_id",
            "option_order",
        ),
    )
