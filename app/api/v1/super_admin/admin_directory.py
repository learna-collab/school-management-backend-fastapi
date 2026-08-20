from fastapi import APIRouter, HTTPException

from app.core.deps import DBSession, RequireSuperAdmin
from app.schemas.directory.directory_school import (
    DirectoryFeaturedUpdate,
    DirectoryVerificationUpdate,
    DirectoryVisibilityUpdate,
)
from app.services.directory.directory_service import DirectorySchoolService

router = APIRouter(
    prefix="/admin/directory",
    tags=["Admin Directory"],
)

service = DirectorySchoolService()


# =====================================================
# VERIFY
# =====================================================


@router.patch(
    "/schools/{school_id}/verify",
)
async def verify_school(
    school_id,
    payload: DirectoryVerificationUpdate,
    db: DBSession,
    current_user: RequireSuperAdmin,
):
    school = await service.repo.get_by_id(
        db,
        school_id,
    )

    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found",
        )

    school = await service.update_verification(
        db,
        school,
        payload.is_directory_verified,
    )

    return {
        "message": "Directory verification updated",
        "school_id": school.id,
        "is_directory_verified": school.is_directory_verified,
    }


# =====================================================
# FEATURE
# =====================================================


@router.patch(
    "/schools/{school_id}/feature",
)
async def feature_school(
    school_id,
    payload: DirectoryFeaturedUpdate,
    db: DBSession,
    current_user: RequireSuperAdmin,
):
    school = await service.repo.get_by_id(
        db,
        school_id,
    )

    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found",
        )

    try:
        school = await service.update_featured(
            db,
            school,
            payload.is_directory_featured,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "message": "Directory featured status updated",
        "school_id": school.id,
        "is_directory_featured": school.is_directory_featured,
    }


# =====================================================
# PUBLISH / UNPUBLISH
# =====================================================


@router.patch(
    "/schools/{school_id}/publish",
)
async def publish_school(
    school_id,
    payload: DirectoryVisibilityUpdate,
    db: DBSession,
    current_user: RequireSuperAdmin,
):
    school = await service.repo.get_by_id(
        db,
        school_id,
    )

    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found",
        )

    school = await service.update_visibility(
        db,
        school,
        payload.is_directory_visible,
    )

    return {
        "message": "Directory visibility updated",
        "school_id": school.id,
        "is_directory_visible": school.is_directory_visible,
    }
