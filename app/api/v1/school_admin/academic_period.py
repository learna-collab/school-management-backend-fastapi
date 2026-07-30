from fastapi import APIRouter

from app.core.deps import CurrentUser, DBSession, RequireSchoolAdmin
from app.schemas.academic_period import (
    AcademicPeriodOptionsResponse,
    SchoolAcademicPeriodResponse,
    UpdateSchoolAcademicPeriodRequest,
)
from app.services.school_academic_period_service import (
    SchoolAcademicPeriodService,
)

router = APIRouter(
    prefix="/school-admin/academic-period",
    tags=["School Academic Period"],
)

service = SchoolAcademicPeriodService()


@router.get(
    "/options",
    response_model=AcademicPeriodOptionsResponse,
)
async def get_options(
    db: DBSession,
    _: RequireSchoolAdmin,
):
    return await service.get_options(db)


@router.get(
    "/current",
    response_model=SchoolAcademicPeriodResponse | None,
)
async def get_current_period(
    db: DBSession,
    current_user: CurrentUser,
):
    return await service.get_current(
        db,
        current_user.school_id,
    )


@router.put(
    "/current",
    response_model=SchoolAcademicPeriodResponse,
)
async def update_current_period(
    payload: UpdateSchoolAcademicPeriodRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.update_current(
        db,
        current_user.school_id,
        payload.session_id,
        payload.term_id,
    )
