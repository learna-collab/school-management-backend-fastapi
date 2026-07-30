from datetime import date

from sqlalchemy import Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class AcademicSession(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "academic_sessions"

    # Example: 2026/2027
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    lessons = relationship("Lesson", back_populates="session")
    result_batches = relationship("ResultBatch", back_populates="session")
    attendance_sheets = relationship(
        "AttendanceSheet",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    cbt_exams = relationship(
        "CBTExam",
        back_populates="session",
    )
