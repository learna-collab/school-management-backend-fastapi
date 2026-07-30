from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.core.deps import DBSession, RequireSuperAdmin
from app.schemas.lesson import (
    LessonResponse,
    SimpleClassResponse,
    SimpleSessionResponse,
    SimpleSubjectResponse,
    SimpleTermResponse,
)
from app.services.lesson_service import LessonService

router = APIRouter(
    prefix="/super-admin/lessons",
    tags=["Super Admin Lessons"],
)

service = LessonService()


@router.get(
    "/classes",
    response_model=list[SimpleClassResponse],
)
async def get_classes(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_classes(db)


@router.get(
    "/subjects",
    response_model=list[SimpleSubjectResponse],
)
async def get_subjects(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_subjects(db)


@router.get(
    "/sessions",
    response_model=list[SimpleSessionResponse],
)
async def get_sessions(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_sessions(db)


@router.get(
    "/terms",
    response_model=list[SimpleTermResponse],
)
async def get_terms(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_terms(db)


@router.post(
    "/upload",
    response_model=LessonResponse,
)
async def upload_lesson(
    db: DBSession,
    current_user: RequireSuperAdmin,
    class_template_id: Annotated[UUID, Form(...)],
    subject_template_id: Annotated[UUID, Form(...)],
    session_id: Annotated[UUID, Form(...)],
    term_id: Annotated[UUID, Form(...)],
    week_number: Annotated[int, Form(...)],
    lesson_day: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
):
    return await service.upload_lesson(
        db=db,
        created_by=current_user.id,
        class_template_id=class_template_id,
        subject_template_id=subject_template_id,
        session_id=session_id,
        term_id=term_id,
        week_number=week_number,
        lesson_day=lesson_day,
        file=file,
    )


@router.get(
    "",
    response_model=list[LessonResponse],
)
async def list_lessons(
    db: DBSession,
    _: RequireSuperAdmin,
    class_template_id: Annotated[UUID, Query(...)],
    subject_template_id: Annotated[UUID, Query(...)],
    session_id: Annotated[UUID, Query(...)],
    term_id: Annotated[UUID, Query(...)],
    week_number: Annotated[int | None, Query()] = None,
):
    return await service.get_lessons(
        db=db,
        class_template_id=class_template_id,
        subject_template_id=subject_template_id,
        session_id=session_id,
        term_id=term_id,
        week_number=week_number,
    )


@router.get(
    "/{lesson_id}",
    response_model=LessonResponse,
)
async def get_lesson(
    lesson_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_lesson(db, lesson_id)


@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    await service.delete(db, lesson_id)

    return {"message": "Lesson deleted successfully"}
