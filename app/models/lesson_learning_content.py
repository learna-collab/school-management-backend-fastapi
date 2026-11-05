from datetime import datetime
from uuid import UUID as PyUUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class LessonLearningContent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lesson_learning_contents"

    __table_args__ = (
        UniqueConstraint(
            "lesson_id",
            "version",
            name="uq_lesson_learning_contents_lesson_version",
        ),
        CheckConstraint(
            "version >= 1",
            name="version_positive",
        ),
        CheckConstraint(
            "status IN ('GENERATED', 'REVIEWED', 'PUBLISHED', 'FAILED')",
            name="valid_status",
        ),
    )

    lesson_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    school_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="GENERATED",
        server_default="GENERATED",
        index=True,
    )

    content: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    generation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    review_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    generated_by: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    reviewed_by: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    published_by: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    lesson = relationship("Lesson")
    school = relationship("School")

    generator = relationship("User", foreign_keys=[generated_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    publisher = relationship("User", foreign_keys=[published_by])

    student_progress = relationship(
        "StudentLearningProgress",
        back_populates="learning_content",
        cascade="all, delete-orphan",
    )
