from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class AcademicTemplate(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "academic_templates"

    name: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    class_templates = relationship(
        "ClassTemplate",
        back_populates="academic_template",
        cascade="all, delete-orphan",
    )

    subject_templates = relationship(
        "SubjectTemplate",
        back_populates="academic_template",
        cascade="all, delete-orphan",
    )
