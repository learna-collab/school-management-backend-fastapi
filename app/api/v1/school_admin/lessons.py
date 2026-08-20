from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import DBSession, RequireSchoolAdmin
from app.repositories.lesson_repository import LessonRepository
from app.schemas.lesson import LessonResponse

router = APIRouter(
    prefix="/school-admin/lessons",
    tags=["School Admin Lessons"],
)

repository = LessonRepository()


@router.get("", response_model=list[LessonResponse])
async def list_lessons(
    db: DBSession,
    current_user: RequireSchoolAdmin,
    class_id: UUID = Query(...),
    session_id: UUID = Query(...),
    term_id: UUID = Query(...),
    week_number: int | None = Query(None),
):
    lessons = await repository.get_school_lessons(
        db=db,
        school_id=current_user.school_id,
        class_id=class_id,
        session_id=session_id,
        term_id=term_id,
        week_number=week_number,
    )
    return lessons


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: UUID,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    lesson = await repository.get_school_lesson_by_id(
        db=db,
        school_id=current_user.school_id,
        lesson_id=lesson_id,
    )

    if lesson is None:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found.",
        )

    return lesson
