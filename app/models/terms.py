from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class Term(
    Base,
    UUIDMixin,
    TimestampMixin,
    TenantMixin,
):
    __tablename__ = "terms"

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_sessions.id"),
        nullable=False,
    )

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
        back_populates="term",
        cascade="all, delete-orphan",
    )
