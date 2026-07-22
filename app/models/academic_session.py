from datetime import date

from sqlalchemy import Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class AcademicSession(
    Base,
    UUIDMixin,
    TimestampMixin,
    TenantMixin,
):
    __tablename__ = "academic_sessions"

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
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
        default=False,
    )
    cbt_exams = relationship(
        "CBTExam",
        back_populates="session",
        cascade="all, delete-orphan",
    )
