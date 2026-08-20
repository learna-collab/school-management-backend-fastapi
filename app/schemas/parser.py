from typing import Optional

from pydantic import BaseModel


class ParsedALF(BaseModel):
    independent_reading: Optional[str] = None
    mini_lesson: Optional[str] = None
    case_study: Optional[str] = None
    project_based_learning: Optional[str] = None
    evaluation: Optional[str] = None


class ParsedLesson(BaseModel):
    week_number: int
    lesson_day: str | None = None
    title: str
    topic: Optional[str] = None
    objectives: Optional[str] = None
    teacher_notes: Optional[str] = None
    alf: ParsedALF
