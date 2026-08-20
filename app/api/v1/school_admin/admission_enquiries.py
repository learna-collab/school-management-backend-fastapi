from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from app.core.deps import (
    DBSession,
    RequireSchoolAdmin,
)
from app.models.admission_enquiry import (
    AdmissionEnquiryStatus,
)
from app.schemas.directory.admission_enquiry import (
    AdmissionEnquiryAdminResponse,
    AdmissionEnquiryResponse,
    AdmissionEnquiryStatusUpdate,
)
from app.services.directory.admission_enquiry_service import (
    AdmissionEnquiryService,
)

router = APIRouter(
    prefix="/school-admin/directory/admission-enquiries",
    tags=["School Admin Admission Enquiries"],
)

service = AdmissionEnquiryService()


@router.get(
    "",
    response_model=list[AdmissionEnquiryAdminResponse],
)
async def list_admission_enquiries(
    db: DBSession,
    current_user: RequireSchoolAdmin,
    status_filter: Annotated[
        AdmissionEnquiryStatus | None,
        Query(alias="status"),
    ] = None,
):
    enquiries = await service.get_school_enquiries(
        db=db,
        school_id=current_user.school_id,
        status_filter=status_filter,
    )

    return [
        {
            "id": enquiry.id,
            "school_id": enquiry.school_id,
            "admission_id": enquiry.admission_id,
            "parent_name": enquiry.parent_name,
            "email": enquiry.email,
            "phone": enquiry.phone,
            "student_name": enquiry.student_name,
            "student_class": enquiry.student_class,
            "message": enquiry.message,
            "status": enquiry.status,
            "created_at": enquiry.created_at,
            "updated_at": enquiry.updated_at,
            "admission_title": (enquiry.admission.title if enquiry.admission else None),
            "session_name": (
                enquiry.admission.session_name if enquiry.admission else None
            ),
        }
        for enquiry in enquiries
    ]


@router.get(
    "/{enquiry_id}",
    response_model=AdmissionEnquiryAdminResponse,
)
async def get_admission_enquiry(
    enquiry_id: UUID,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    enquiry = await service.get_by_id(
        db,
        enquiry_id,
    )

    if not enquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission enquiry not found.",
        )

    if enquiry.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access another school's enquiry.",
        )

    return {
        "id": enquiry.id,
        "school_id": enquiry.school_id,
        "admission_id": enquiry.admission_id,
        "parent_name": enquiry.parent_name,
        "email": enquiry.email,
        "phone": enquiry.phone,
        "student_name": enquiry.student_name,
        "student_class": enquiry.student_class,
        "message": enquiry.message,
        "status": enquiry.status,
        "created_at": enquiry.created_at,
        "updated_at": enquiry.updated_at,
        "admission_title": (enquiry.admission.title if enquiry.admission else None),
        "session_name": (enquiry.admission.session_name if enquiry.admission else None),
    }


@router.patch(
    "/{enquiry_id}/status",
    response_model=AdmissionEnquiryResponse,
)
async def update_enquiry_status(
    enquiry_id: UUID,
    payload: AdmissionEnquiryStatusUpdate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    enquiry = await service.get_by_id(
        db,
        enquiry_id,
    )

    if not enquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission enquiry not found.",
        )

    if enquiry.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot modify another school's enquiry.",
        )

    return await service.update_status(
        db=db,
        enquiry=enquiry,
        status=payload.status,
    )


@router.delete(
    "/{enquiry_id}",
)
async def delete_admission_enquiry(
    enquiry_id: UUID,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    enquiry = await service.get_by_id(
        db,
        enquiry_id,
    )

    if not enquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission enquiry not found.",
        )

    if enquiry.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete another school's enquiry.",
        )

    await service.delete_enquiry(
        db,
        enquiry,
    )

    return {
        "message": "Admission enquiry deleted successfully.",
    }


@router.get(
    "/stats",
)
async def get_admission_enquiry_stats(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.get_enquiry_counts(
        db,
        current_user.school_id,
    )
