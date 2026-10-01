from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import DBSession, RequireSuperAdmin
from app.models.enums.alf import ALFSessionStatus
from app.schemas.teacher_alf_usage import (
    ALFLessonUsageResponse,
    ALFTeacherUsageResponse,
    ALFUsageSessionResponse,
    ALFUsageStatsResponse,
)
from app.services.teacher_alf_usage_service import (
    TeacherALFUsageService,
)

router = APIRouter(
    prefix="/super-admin/alf",
    tags=["Super Admin ALF"],
)

service = TeacherALFUsageService()


@router.get(
    "/usage",
    response_model=list[ALFUsageSessionResponse],
)
async def get_alf_usage(
    db: DBSession,
    _: RequireSuperAdmin,
    teacher_id: Annotated[UUID | None, Query()] = None,
    lesson_id: Annotated[UUID | None, Query()] = None,
    class_id: Annotated[UUID | None, Query()] = None,
    session_status: Annotated[
        ALFSessionStatus | None,
        Query(alias="status"),
    ] = None,
):
    return await service.get_sessions(
        db=db,
        teacher_id=teacher_id,
        lesson_id=lesson_id,
        class_id=class_id,
        session_status=session_status,
    )


@router.get(
    "/usage/{session_id}",
    response_model=ALFUsageSessionResponse,
)
async def get_alf_usage_session(
    session_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_session(
        db=db,
        session_id=session_id,
    )


@router.get(
    "/lessons/{lesson_id}/usage",
    response_model=ALFLessonUsageResponse,
)
async def get_lesson_alf_usage(
    lesson_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_lesson_usage(
        db=db,
        lesson_id=lesson_id,
    )


@router.get(
    "/teachers/{teacher_id}/usage",
    response_model=ALFTeacherUsageResponse,
)
async def get_teacher_alf_usage(
    teacher_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_teacher_usage(
        db=db,
        teacher_id=teacher_id,
    )


@router.get(
    "/stats",
    response_model=ALFUsageStatsResponse,
)
async def get_alf_stats(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_stats(db)
