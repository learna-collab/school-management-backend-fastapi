from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class AttendanceSheet(
    Base,
    UUIDMixin,
    TenantMixin,
    TimestampMixin,
):
    __tablename__ = "attendance_sheets"

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("classes.id"),
        index=True,
    )

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_sessions.id"),
        index=True,
    )

    term_id: Mapped[UUID] = mapped_column(
        ForeignKey("terms.id"),
        index=True,
    )

    attendance_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    marked_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
    )

    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    records = relationship(
        "AttendanceRecord",
        back_populates="sheet",
        cascade="all, delete-orphan",
    )
    session = relationship(
        "AcademicSession",
        back_populates="attendance_sheets",
    )

    term = relationship(
        "Term",
        back_populates="attendance_sheets",
    )

    __table_args__ = (
        UniqueConstraint(
            "class_id",
            "session_id",
            "term_id",
            "attendance_date",
            name="uq_attendance_sheet",
        ),
    )
