from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from app.models.finance.payment import Payment
    from app.models.student_profile import StudentProfile
    from app.models.term import Term

    from app.models.academic_session import AcademicSession
    from app.models.finance.fee_category import FeeCategory


class StudentFee(
    Base,
    UUIDMixin,
    TenantMixin,
    TimestampMixin,
):
    __tablename__ = "student_fees"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "fee_category_id",
            "session_id",
            "term_id",
            name="uq_student_fee_period",
        ),
    )

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "student_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    fee_category_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "fee_categories.id",
        ),
        nullable=False,
        index=True,
    )

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "academic_sessions.id",
        ),
        nullable=False,
        index=True,
    )

    term_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "terms.id",
        ),
        nullable=False,
        index=True,
    )

    amount_due: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    student = relationship(
        "StudentProfile",
        back_populates="student_fees",
    )

    fee_category = relationship(
        "FeeCategory",
        back_populates="student_fees",
    )

    session = relationship(
        "AcademicSession",
    )

    term = relationship(
        "Term",
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="student_fee",
        cascade="all, delete-orphan",
    )
