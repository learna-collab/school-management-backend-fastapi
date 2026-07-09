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


class ClassTemplate(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "class_templates"

    academic_template_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "academic_templates.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
    )

    level: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    sort_order: Mapped[int] = mapped_column(
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    academic_template = relationship(
        "AcademicTemplate",
        back_populates="class_templates",
    )

    subjects = relationship(
        "TemplateClassSubject",
        back_populates="class_template",
        cascade="all, delete-orphan",
    )
