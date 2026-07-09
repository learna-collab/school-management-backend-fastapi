from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    UniqueConstraint,
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


class TemplateClassSubject(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "template_class_subjects"

    class_template_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "class_templates.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    subject_template_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "subject_templates.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    class_template = relationship(
        "ClassTemplate",
        back_populates="subjects",
    )

    subject_template = relationship(
        "SubjectTemplate",
        back_populates="classes",
    )

    __table_args__ = (
        UniqueConstraint(
            "class_template_id",
            "subject_template_id",
            name="uq_template_class_subject",
        ),
    )
