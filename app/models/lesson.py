from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Lesson(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lessons"

    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # GENERIC TEMPLATE LINKS
    class_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("class_templates.id"),
        nullable=False,
    )

    subject_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subject_templates.id"),
        nullable=False,
    )

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id"),
        nullable=False,
    )

    term_id = Column(
        UUID(as_uuid=True),
        ForeignKey("terms.id"),
        nullable=False,
    )

    week_number = Column(Integer, nullable=False)

    title = Column(String(255), nullable=False)
    topic = Column(String(255), nullable=False)

    objectives = Column(Text, nullable=False)
    teacher_notes = Column(Text, nullable=True)

    file_url = Column(Text, nullable=True)

    is_published = Column(Boolean, default=True)

    # relationships
    class_template = relationship("ClassTemplate")
    subject_template = relationship("SubjectTemplate")

    alf = relationship(
        "LessonALF",
        back_populates="lesson",
        uselist=False,
        cascade="all, delete-orphan",
    )
    session = relationship("AcademicSession", back_populates="lessons")

    term = relationship("Term", back_populates="lessons")
