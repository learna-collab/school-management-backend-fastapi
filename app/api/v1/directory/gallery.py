from fastapi import APIRouter, HTTPException, status

from app.core.deps import DBSession
from app.services.directory.directory_service import DirectorySchoolService
from app.services.directory.gallery_service import SchoolGalleryService

router = APIRouter(
    prefix="/directory/schools",
    tags=["Directory Gallery"],
)

gallery_service = SchoolGalleryService()
school_service = DirectorySchoolService()


@router.get("/{slug}/gallery")
async def get_school_gallery(
    slug: str,
    db: DBSession,
):
    """Public gallery for a school."""
    school = await school_service.get_school_by_slug(
        db,
        slug,
    )

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found.",
        )

    return await gallery_service.get_gallery(
        db,
        school.id,
    )


@router.get("/{slug}/gallery/cover")
async def get_school_cover_image(
    slug: str,
    db: DBSession,
):
    """Returns only the school's cover image."""
    school = await school_service.get_school_by_slug(
        db,
        slug,
    )

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found.",
        )

    images = await gallery_service.get_gallery(
        db,
        school.id,
    )

    cover = next(
        (image for image in images if image.is_cover),
        None,
    )

    if not cover:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover image not found.",
        )

    return cover
