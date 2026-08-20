import uuid
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.admission_enquiry import AdmissionEnquiry
    from app.models.school import School


class AdmissionCategory(str, Enum):
    NURSERY = "NURSERY"
    PRIMARY = "PRIMARY"
    JSS1 = "JSS1"
    JSS2 = "JSS2"
    JSS3 = "JSS3"
    SS1 = "SS1"
    SS2 = "SS2"
    SS3 = "SS3"
    TRANSFER = "TRANSFER"


class SchoolAdmission(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "school_admissions"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    session_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    category: Mapped[AdmissionCategory] = mapped_column(
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    requirements: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    application_fee: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    application_deadline: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    brochure_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    brochure_public_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    application_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_open: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    school: Mapped["School"] = relationship(
        "School",
        back_populates="admissions",
    )
    enquiries: Mapped[list["AdmissionEnquiry"]] = relationship(
        "AdmissionEnquiry",
        back_populates="admission",
        cascade="all, delete-orphan",
    )
