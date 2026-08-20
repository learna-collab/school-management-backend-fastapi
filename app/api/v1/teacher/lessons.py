from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import DBSession, RequireTeacher
from app.repositories.lesson_repository import LessonRepository
from app.schemas.lesson import LessonResponse

router = APIRouter(
    prefix="/teacher/lessons",
    tags=["Teacher Lessons"],
)

repository = LessonRepository()


@router.get("", response_model=list[LessonResponse])
async def list_lessons(
    db: DBSession,
    current_user: RequireTeacher,
    class_id: UUID = Query(...),
    # keep subject filter
    session_id: UUID = Query(...),
    term_id: UUID = Query(...),
    week_number: int | None = Query(None),
):
    lessons = await repository.get_teacher_lessons(
        db=db,
        teacher_id=current_user.id,
        class_id=class_id,
        # pass subject
        session_id=session_id,
        term_id=term_id,
        week_number=week_number,
    )

    return lessons


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: UUID,
    db: DBSession,
    current_user: RequireTeacher,
):
    lesson = await repository.get_teacher_lesson_by_id(
        db=db,
        teacher_id=current_user.id,
        lesson_id=lesson_id,
    )

    if lesson is None:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found.",
        )

    return lesson
