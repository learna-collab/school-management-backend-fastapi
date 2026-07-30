from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Term(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "terms"

    # Example: First Term, Second Term, Third Term
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    # Controls display order
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    lessons = relationship("Lesson", back_populates="term")
    result_batches = relationship("ResultBatch", back_populates="term")
    attendance_sheets = relationship(
        "AttendanceSheet",
        back_populates="term",
        cascade="all, delete-orphan",
    )

    cbt_exams = relationship(
        "CBTExam",
        back_populates="term",
    )
