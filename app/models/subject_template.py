from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
)


class SubjectTemplate(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "subject_templates"

    academic_template_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "academic_templates.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
    )

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    level: Mapped[str] = mapped_column(
        String(50),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    academic_template = relationship(
        "AcademicTemplate",
        back_populates="subject_templates",
    )

    classes = relationship(
        "TemplateClassSubject",
        back_populates="subject_template",
        cascade="all, delete-orphan",
    )
