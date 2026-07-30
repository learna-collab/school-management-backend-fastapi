from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.core.deps import DBSession, RequireSchoolAdmin
from app.schemas.admin_settings import (
    ChangePasswordRequest,
    SchoolSettingsResponse,
    UpdateSchoolSettingsRequest,
)
from app.services.admin_settings_service import AdminSettingsService

router = APIRouter(
    prefix="/school-admin/settings",
    tags=["School Admin Settings"],
)

service = AdminSettingsService()


# ============================================================
# GET SCHOOL SETTINGS
# ============================================================


@router.get(
    "",
    response_model=SchoolSettingsResponse,
)
async def get_school_settings(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.get_settings(
        db=db,
        school_id=current_user.school_id,
    )


# ============================================================
# UPDATE SCHOOL PROFILE
# ============================================================


@router.put(
    "",
    response_model=SchoolSettingsResponse,
)
async def update_school_settings(
    payload: UpdateSchoolSettingsRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.update_settings(
        db=db,
        school_id=current_user.school_id,
        payload=payload,
    )


# ============================================================
# CHANGE PASSWORD
# ============================================================


@router.put(
    "/password",
    status_code=status.HTTP_200_OK,
)
async def change_password(
    payload: ChangePasswordRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    await service.change_password(
        db=db,
        user_id=current_user.id,
        payload=payload,
    )

    return {"message": "Password updated successfully."}


# ============================================================
# UPLOAD SCHOOL LOGO
# ============================================================


@router.post(
    "/logo",
)
async def upload_logo(
    db: DBSession,
    current_user: RequireSchoolAdmin,
    logo: Annotated[UploadFile, File()],
):
    """
    Upload school logo.

    Service should:
        • validate image
        • upload to storage
        • save logo_url
    """
    logo_url = await service.upload_logo(
        db=db,
        school_id=current_user.school_id,
        file=logo,
    )

    return {
        "message": "Logo uploaded successfully.",
        "logo_url": logo_url,
    }
