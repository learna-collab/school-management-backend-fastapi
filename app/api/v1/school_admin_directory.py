from fastapi import APIRouter, HTTPException

from app.core.deps import DBSession, RequireSchoolAdmin
from app.schemas.directory_school import (
    DirectorySchoolDetail,
    DirectorySchoolUpdate,
    DirectoryVisibilityUpdate,
)
from app.services.directory_service import DirectorySchoolService

router = APIRouter(
    prefix="/school-admin/directory",
    tags=["School Admin Directory"],
)

service = DirectorySchoolService()


# =====================================================
# GET OWN DIRECTORY PROFILE
# =====================================================


@router.get(
    "/profile",
    response_model=DirectorySchoolDetail,
)
async def get_directory_profile(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    school = await service.repo.get_by_id(
        db,
        current_user.school_id,
    )

    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found",
        )

    return school


# =====================================================
# UPDATE OWN DIRECTORY PROFILE
# =====================================================


@router.put(
    "/profile",
    response_model=DirectorySchoolDetail,
)
async def update_directory_profile(
    payload: DirectorySchoolUpdate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    school = await service.repo.get_by_id(
        db,
        current_user.school_id,
    )

    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found",
        )

    return await service.update_profile(
        db,
        school,
        payload,
    )


# =====================================================
# PUBLISH / UNPUBLISH
# =====================================================


@router.patch(
    "/visibility",
    response_model=DirectorySchoolDetail,
)
async def update_directory_visibility(
    payload: DirectoryVisibilityUpdate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    school = await service.repo.get_by_id(
        db,
        current_user.school_id,
    )

    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found",
        )

    return await service.update_visibility(
        db,
        school,
        payload.is_directory_visible,
    )
