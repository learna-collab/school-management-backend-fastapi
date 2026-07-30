from uuid import UUID

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class SchoolAcademicPeriod(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "school_academic_periods"

    school_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("academic_sessions.id"),
        nullable=False,
        index=True,
    )

    term_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("terms.id"),
        nullable=False,
        index=True,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    school = relationship(
        "School",
        back_populates="academic_periods",
    )
    session = relationship("AcademicSession")
    term = relationship("Term")
