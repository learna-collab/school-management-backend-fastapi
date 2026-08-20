from app.services.directory.school_service import (
    DirectorySchoolService,
)
from fastapi import APIRouter, HTTPException

from app.core.deps import DBSession
from app.services.directory.facility_service import (
    SchoolFacilityService,
)

router = APIRouter(
    prefix="/directory/schools",
    tags=["Directory Facilities"],
)

facility_service = SchoolFacilityService()
school_service = DirectorySchoolService()


@router.get("/{slug}/facilities")
async def get_school_facilities(
    slug: str,
    db: DBSession,
):
    school = await school_service.get_school_by_slug(
        db,
        slug,
    )

    if not school:
        raise HTTPException(404, "School not found")

    return await facility_service.list_school_facilities(
        db,
        school.id,
    )
