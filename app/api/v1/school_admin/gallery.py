from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel

from app.core.deps import DBSession, RequireSchoolAdmin
from app.models.school_gallery import GalleryCategory
from app.schemas.directory.gallery import SchoolGalleryUpdate
from app.services.cloudinary_service import cloudinary_service
from app.services.directory.gallery_service import SchoolGalleryService

router = APIRouter(
    prefix="/school-admin/directory/gallery",
    tags=["School Admin Gallery"],
)

service = SchoolGalleryService()


class GalleryReorderRequest(BaseModel):
    image_ids: list[UUID]


# =====================================================
# LIST GALLERY
# =====================================================


@router.get("")
async def list_gallery(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.get_gallery(
        db,
        current_user.school_id,
        admin=True,
    )


# =====================================================
# UPLOAD IMAGE
# =====================================================


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def upload_gallery_image(
    db: DBSession,
    current_user: RequireSchoolAdmin,
    image: UploadFile = File(...),
    caption: str | None = Form(None),
    category: GalleryCategory = Form(GalleryCategory.OTHER),
    is_cover: bool = Form(False),
):
    uploaded = await cloudinary_service.upload_file(
        file=image,
        folder=f"school-directory/{current_user.school.slug}/gallery",
    )

    return await service.upload_image(
        db=db,
        school_id=current_user.school_id,
        image_url=uploaded["url"],
        public_id=uploaded["public_id"],
        caption=caption,
        category=category,
        is_cover=is_cover,
    )


# =====================================================
# UPDATE IMAGE
# =====================================================


@router.put("/{image_id}")
async def update_gallery_image(
    image_id: UUID,
    payload: SchoolGalleryUpdate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    image = await service.repo.get_by_id(
        db,
        image_id,
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )

    if image.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot edit another school's gallery.",
        )

    return await service.update_image(
        db,
        image,
        payload,
    )


# =====================================================
# SET COVER IMAGE
# =====================================================


@router.patch("/{image_id}/cover")
async def set_cover_image(
    image_id: UUID,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    image = await service.repo.get_by_id(
        db,
        image_id,
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )

    if image.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed.",
        )

    await service.repo.clear_cover(
        db,
        current_user.school_id,
    )

    image.is_cover = True

    return await service.repo.save(
        db,
        image,
    )


# =====================================================
# REORDER GALLERY
# =====================================================


@router.patch("/reorder")
async def reorder_gallery(
    payload: GalleryReorderRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.reorder_images(
        db,
        current_user.school_id,
        payload.image_ids,
    )


# =====================================================
# DELETE IMAGE
# =====================================================


@router.delete("/{image_id}")
async def delete_gallery_image(
    image_id: UUID,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    image = await service.repo.get_by_id(
        db,
        image_id,
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )

    if image.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed.",
        )

    await cloudinary_service.delete_file(
        public_id=image.public_id,
    )

    await service.delete_image(
        db,
        image,
    )

    return {
        "message": "Image deleted successfully.",
    }
