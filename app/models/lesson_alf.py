from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, UUIDMixin


class LessonALF(Base, UUIDMixin):
    __tablename__ = "lesson_alf"

    lesson_id = Column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    independent_reading = Column(Text)
    mini_lesson = Column(Text)
    case_study = Column(Text)
    project_based_learning = Column(Text)
    evaluation = Column(Text)

    lesson = relationship("Lesson", back_populates="alf")
