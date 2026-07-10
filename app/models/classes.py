from enum import Enum as PyEnum

from sqlalchemy import UUID, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class AcademicLevel(str, PyEnum):
    __slots__ = ()

    NURSERY = "NURSERY"
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"


class Class(
    Base,
    UUIDMixin,
    TenantMixin,
    TimestampMixin,
):
    __tablename__ = "classes"
    template_class_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("class_templates.id"),
        nullable=True,
    )

    # Example:
    # Nursery 1
    # Primary 4
    # JSS 1

    name: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )

    # Nursery
    # Primary
    # Secondary

    level: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    # optional ordering

    sort_order: Mapped[int] = mapped_column(nullable=True)

    # =======================================
    # RELATIONSHIPS
    # =======================================

    enrollments = relationship(
        "StudentEnrollment",
        back_populates="school_class",
        cascade="all, delete-orphan",
    )

    class_subjects = relationship(
        "ClassSubject",
        back_populates="school_class",
        cascade="all, delete-orphan",
    )

    class_teachers = relationship(
        "ClassTeacher",
        back_populates="school_class",
        cascade="all, delete-orphan",
    )

    teacher_assignments = relationship(
        "TeacherClassSubject",
        back_populates="school_class",
        cascade="all, delete-orphan",
    )
