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
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class ClassSubject(
    Base,
    UUIDMixin,
    TenantMixin,
    TimestampMixin,
):
    __tablename__ = "class_subjects"

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "classes.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "subjects.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    school_class = relationship(
        "Class",
        back_populates="class_subjects",
    )

    subject = relationship(
        "Subject",
        back_populates="class_subjects",
    )

    __table_args__ = (
        UniqueConstraint(
            "class_id",
            "subject_id",
            name="uq_class_subject",
        ),
    )
