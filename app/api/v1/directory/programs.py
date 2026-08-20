from app.services.directory.school_service import (
    DirectorySchoolService,
)
from fastapi import APIRouter, HTTPException, status

from app.core.deps import DBSession
from app.services.directory.program_service import (
    SchoolProgramService,
)

router = APIRouter(
    prefix="/directory/schools",
    tags=["Directory Programs"],
)

program_service = SchoolProgramService()
school_service = DirectorySchoolService()


@router.get("/{slug}/programs")
async def get_school_programs(
    slug: str,
    db: DBSession,
):
    school = await school_service.get_school_by_slug(
        db,
        slug,
    )

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found",
        )

    return await program_service.get_programs(
        db,
        school.id,
    )
