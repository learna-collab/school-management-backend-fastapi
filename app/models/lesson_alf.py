from sqlalchemy import Column, ForeignKey, Integer, Text
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

    # Content sections
    independent_reading = Column(Text)
    mini_lesson = Column(Text)
    case_study = Column(Text)
    project_based_learning = Column(Text)
    evaluation = Column(Text)

    # Duration in minutes for guided lesson mode
    independent_reading_duration = Column(Integer, default=7)
    mini_lesson_duration = Column(Integer, default=7)
    case_study_duration = Column(Integer, default=7)
    project_based_learning_duration = Column(Integer, default=17)
    evaluation_duration = Column(Integer, default=2)

    lesson = relationship("Lesson", back_populates="alf")
