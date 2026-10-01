from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import DBSession, RequireTeacher
from app.models.enums.alf import ALFSessionStatus
from app.schemas.teacher_alf_session import (
    ALFSessionProgressRequest,
    ALFSessionResponse,
    ALFSessionStartRequest,
)
from app.services.teacher_alf_session_service import (
    TeacherALFSessionService,
)

router = APIRouter(
    prefix="/teacher/alf",
    tags=["Teacher ALF"],
)

service = TeacherALFSessionService()


@router.post(
    "/lessons/{lesson_id}/start",
    response_model=ALFSessionResponse,
)
async def start_alf_session(
    lesson_id: UUID,
    payload: ALFSessionStartRequest,
    db: DBSession,
    current_user: RequireTeacher,
):
    session = await service.start_session(
        db=db,
        teacher_id=current_user.id,
        school_id=current_user.school_id,
        lesson_id=lesson_id,
        class_id=payload.class_id,
    )

    return service.to_response(session)


@router.patch(
    "/sessions/{session_id}",
    response_model=ALFSessionResponse,
)
async def update_alf_progress(
    session_id: UUID,
    payload: ALFSessionProgressRequest,
    db: DBSession,
    current_user: RequireTeacher,
):
    if all(
        value is None
        for value in (
            payload.independent_reading_completed,
            payload.mini_lesson_completed,
            payload.case_study_completed,
            payload.project_based_learning_completed,
            payload.evaluation_completed,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one ALF progress field must be provided.",
        )

    session = await service.update_progress(
        db=db,
        teacher_id=current_user.id,
        session_id=session_id,
        independent_reading_completed=(payload.independent_reading_completed),
        mini_lesson_completed=payload.mini_lesson_completed,
        case_study_completed=payload.case_study_completed,
        project_based_learning_completed=(payload.project_based_learning_completed),
        evaluation_completed=payload.evaluation_completed,
    )

    return service.to_response(session)


@router.post(
    "/sessions/{session_id}/complete",
    response_model=ALFSessionResponse,
)
async def complete_alf_session(
    session_id: UUID,
    db: DBSession,
    current_user: RequireTeacher,
):
    session = await service.complete_session(
        db=db,
        teacher_id=current_user.id,
        session_id=session_id,
    )

    return service.to_response(session)


@router.get(
    "/sessions",
    response_model=list[ALFSessionResponse],
)
async def get_alf_sessions(
    db: DBSession,
    current_user: RequireTeacher,
    class_id: Annotated[UUID | None, Query()] = None,
    lesson_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[ALFSessionStatus | None, Query()] = None,
):
    sessions = await service.get_teacher_sessions(
        db=db,
        teacher_id=current_user.id,
        class_id=class_id,
        lesson_id=lesson_id,
        status=status,
    )

    return [service.to_response(session) for session in sessions]


@router.get(
    "/sessions/{session_id}",
    response_model=ALFSessionResponse,
)
async def get_alf_session(
    session_id: UUID,
    db: DBSession,
    current_user: RequireTeacher,
):
    session = await service.get_session(
        db=db,
        teacher_id=current_user.id,
        session_id=session_id,
    )

    return service.to_response(session)
