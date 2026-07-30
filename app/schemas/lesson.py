from pydantic import BaseModel, ConfigDict


class LessonALFResponse(BaseModel):
    independent_reading: str | None = None
    mini_lesson: str | None = None
    case_study: str | None = None
    project_based_learning: str | None = None
    evaluation: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SimpleClassResponse(BaseModel):
    id: str
    name: str


class SimpleSubjectResponse(BaseModel):
    id: str
    name: str


class SimpleSessionResponse(BaseModel):
    id: str
    name: str


class SimpleTermResponse(BaseModel):
    id: str
    name: str


class LessonResponse(BaseModel):
    id: str

    week_number: int
    lesson_day: str

    class_name: str
    subject_name: str

    title: str
    topic: str

    objectives: str | None = None
    teacher_notes: str | None = None

    file_url: str | None = None
    is_published: bool = True

    alf: LessonALFResponse | None = None

    model_config = ConfigDict(from_attributes=True)
