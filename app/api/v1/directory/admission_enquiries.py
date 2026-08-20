from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.core.deps import DBSession
from app.schemas.directory.admission_enquiry import (
    AdmissionEnquiryCreate,
    AdmissionEnquiryResponse,
)
from app.services.admission_service import SchoolAdmissionService
from app.services.directory.admission_enquiry_service import (
    AdmissionEnquiryService,
)
from app.services.directory.directory_service import DirectorySchoolService

router = APIRouter(
    prefix="/directory",
    tags=["Directory Admission Enquiries"],
)

enquiry_service = AdmissionEnquiryService()
admission_service = SchoolAdmissionService()
school_service = DirectorySchoolService()


@router.post(
    "/schools/{slug}/admissions/{admission_id}/enquiries",
    response_model=AdmissionEnquiryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_admission_enquiry(
    slug: str,
    admission_id: UUID,
    payload: AdmissionEnquiryCreate,
    db: DBSession,
):
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
            detail=(
                "Admission not found or admission is no longer accepting enquiries."
            ),
        )

    return await enquiry_service.create_enquiry(
        db=db,
        school_id=school.id,
        admission_id=admission.id,
        payload=payload,
    )
