from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class ResultBatch(
    Base,
    UUIDMixin,
    TenantMixin,
    TimestampMixin,
):
    __tablename__ = "result_batches"

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

    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="DRAFT",
    )
    # DRAFT
    # SUBMITTED
    # APPROVED
    # REJECTED
    # PUBLISHED

    requires_review: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    records = relationship(
        "ResultRecord",
        back_populates="batch",
        cascade="all, delete-orphan",
    )

    summaries = relationship(
        "ResultSummary",
        back_populates="batch",
        cascade="all, delete-orphan",
    )

    approvals = relationship(
        "ResultApproval",
        back_populates="batch",
        cascade="all, delete-orphan",
    )

    school_class = relationship("Class")
    session = relationship("AcademicSession")
    term = relationship("Term")
    creator = relationship("User")
    school = relationship("School")
