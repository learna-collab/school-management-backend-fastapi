from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_settings_repository import AdminSettingsRepository
from app.schemas.admin_settings import (
    ChangePasswordRequest,
    UpdateSchoolSettingsRequest,
)
from app.services.cloudinary_service import cloudinary_service
from app.utils.helper import hash_password, verify_password


class AdminSettingsService:
    """Business logic for School Admin settings."""

    def __init__(self):
        self.repository = AdminSettingsRepository()

    # =====================================================
    # SETTINGS
    # =====================================================

    async def get_settings(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        school = await self.repository.get_school(
            db,
            school_id,
        )

        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School not found.",
            )

        return school

    async def update_settings(
        self,
        db: AsyncSession,
        school_id: UUID,
        payload: UpdateSchoolSettingsRequest,
    ):
        school = await self.repository.get_school(
            db,
            school_id,
        )

        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School not found.",
            )

        return await self.repository.update_school(
            db=db,
            school=school,
            **payload.model_dump(exclude_unset=True),
        )

    # =====================================================
    # PASSWORD
    # =====================================================

    async def change_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        payload: ChangePasswordRequest,
    ):
        user = await self.repository.get_user(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # Always verify against hashed password in users table
        current_hash = user.password_hash

        if not current_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password not configured.",
            )

        if not verify_password(payload.current_password, current_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

        if verify_password(payload.new_password, current_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the current password.",
            )

        # Hash for users table
        new_hash = hash_password(payload.new_password)

        # Update hashed password in users table
        user.password_hash = new_hash

        # Update plain password in user_credentials table
        if user.credential:
            user.credential.password = payload.new_password

        await db.commit()
        await db.refresh(user)

        return {"message": "Password updated successfully."}

    # =====================================================
    # LOGO
    # =====================================================

    async def upload_logo(
        self,
        db: AsyncSession,
        school_id: UUID,
        file: UploadFile,
    ):
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Only image files are allowed.",
            )

        logo_url = await cloudinary_service.upload_file(
            file=file,
            folder="schools/logos",
            public_id=str(school_id),
            resource_type="image",
        )

        school = await self.repository.update_logo(
            db=db,
            school_id=school_id,
            logo_url=logo_url,
        )

        await db.commit()
        await db.refresh(school)

        return {
            "message": "School logo uploaded successfully.",
            "logo_url": school.logo_url,
        }
