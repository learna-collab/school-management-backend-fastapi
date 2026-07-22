from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    TenantMixin,
    UUIDMixin,
)


class Subject(
    Base,
    UUIDMixin,
    TenantMixin,
):
    __tablename__ = "subjects"
    template_subject_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subject_templates.id"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255))

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    is_custom: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    cbt_exams = relationship(
        "CBTExam",
        back_populates="subject",
        cascade="all, delete-orphan",
    )

    teacher_assignments = relationship(
        "TeacherClassSubject",
        back_populates="subject",
        cascade="all, delete-orphan",
    )

    class_subjects = relationship(
        "ClassSubject",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
