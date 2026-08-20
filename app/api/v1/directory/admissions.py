from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.core.deps import DBSession
from app.schemas.directory.admission import (
    PublicAdmissionResponse,
)
from app.services.admission_service import SchoolAdmissionService
from app.services.directory.directory_service import DirectorySchoolService

router = APIRouter(
    prefix="/directory",
    tags=["Directory Admissions"],
)

admission_service = SchoolAdmissionService()
school_service = DirectorySchoolService()


# =====================================================
# ALL SCHOOLS WITH OPEN ADMISSIONS
# =====================================================


@router.get(
    "/admissions/open",
)
async def get_open_admissions(
    db: DBSession,
):
    """
    Return all currently open admission campaigns.

    Used by the directory discovery/search page.
    """
    admissions = await admission_service.get_all_open_admissions(
        db,
    )

    return admissions


# =====================================================
# SCHOOL ADMISSIONS
# =====================================================


@router.get(
    "/schools/{slug}/admissions",
)
async def get_school_admissions(
    slug: str,
    db: DBSession,
):
    """Return currently open admissions for a school."""
    school = await school_service.get_school_by_slug(
        db,
        slug,
    )

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found.",
        )

    admissions = await admission_service.get_open_school_admissions(
        db,
        school.id,
    )

    return admissions


# =====================================================
# ADMISSION DETAILS
# =====================================================


@router.get(
    "/schools/{slug}/admissions/{admission_id}",
    response_model=PublicAdmissionResponse,
)
async def get_admission_details(
    slug: str,
    admission_id: UUID,
    db: DBSession,
):
    """Return one currently active admission campaign."""
    school = await school_service.get_school_by_slug(
        db,
        slug,
    )

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found.",
        )

    admission = await admission_service.get_public_admission(
        db,
        school.id,
        admission_id,
    )

    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found or admission is closed.",
        )

    return admission
