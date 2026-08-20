from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.school_admission import SchoolAdmission
    from app.models.school_facility import SchoolFacility
    from app.models.school_gallery import SchoolGallery
    from app.models.school_program import SchoolProgram
    from app.models.user import User


class School(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "schools"

    # =====================================================
    # BASIC SCHOOL INFORMATION
    # =====================================================

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    whatsapp_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # =====================================================
    # SCHOOL CLASSIFICATION
    # =====================================================

    school_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    ownership_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    founded_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # =====================================================
    # EXISTING PLATFORM INFORMATION
    # =====================================================

    academic_setup_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=True,
    )

    subscription_plan: Mapped[str] = mapped_column(
        String(50),
        default="basic",
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    contact_person: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    average_fee_range: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    population_range: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    referral_source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # =====================================================
    # DIRECTORY
    # =====================================================

    is_directory_visible: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=True,
        index=True,
    )

    is_directory_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=True,
        index=True,
    )

    is_directory_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=True,
        index=True,
    )

    directory_cover_image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="school",
        cascade="all, delete-orphan",
    )

    academic_periods = relationship(
        "SchoolAcademicPeriod",
        back_populates="school",
        cascade="all, delete-orphan",
    )
    """ facilities: Mapped[list["SchoolFacility"]] = relationship(
        "SchoolFacility",
        back_populates="school",
        cascade="all, delete-orphan",
    )
    programs: Mapped[list["SchoolProgram"]] = relationship(
        "SchoolProgram",
        back_populates="school",
        cascade="all, delete-orphan",
    )
    gallery: Mapped[list["SchoolGallery"]] = relationship(
        "SchoolGallery",
        back_populates="school",
        cascade="all, delete-orphan",
    )
    admissions: Mapped[list["SchoolAdmission"]] = relationship(
        "SchoolAdmission",
        back_populates="school",
        cascade="all, delete-orphan",
    ) """
