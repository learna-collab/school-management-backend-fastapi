import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.school import School
    from app.models.school_admission import SchoolAdmission


class AdmissionEnquiryStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    VISIT_SCHEDULED = "VISIT_SCHEDULED"
    CONVERTED = "CONVERTED"
    CLOSED = "CLOSED"


class AdmissionEnquiry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "admission_enquiries"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    admission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "school_admissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    parent_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    phone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    student_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    student_class: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[AdmissionEnquiryStatus] = mapped_column(
        default=AdmissionEnquiryStatus.NEW,
        nullable=False,
        index=True,
    )

    school: Mapped["School"] = relationship(
        "School",
    )

    admission: Mapped["SchoolAdmission"] = relationship(
        "SchoolAdmission",
        back_populates="enquiries",
    )
