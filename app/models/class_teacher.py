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


class ClassTeacher(
    Base,
    UUIDMixin,
    TenantMixin,
    TimestampMixin,
):
    __tablename__ = "class_teachers"

    teacher_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "classes.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    teacher = relationship(
        "User",
        back_populates="class_assignments",
    )

    school_class = relationship(
        "Class",
        back_populates="class_teachers",
    )

    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "class_id",
            name="uq_teacher_class",
        ),
    )
