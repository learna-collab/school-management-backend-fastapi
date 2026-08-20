from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.core.deps import (
    DBSession,
    RequireSchoolAdmin,
)
from app.schemas.directory.admission import (
    AdmissionStatusUpdate,
    SchoolAdmissionCreate,
    SchoolAdmissionResponse,
    SchoolAdmissionUpdate,
)
from app.services.admission_service import SchoolAdmissionService
from app.services.cloudinary_service import (
    cloudinary_service,
)

router = APIRouter(
    prefix="/school-admin/directory/admissions",
    tags=["School Admin Admissions"],
)

service = SchoolAdmissionService()


# =====================================================
# LIST ADMISSIONS
# =====================================================


@router.get(
    "",
    response_model=list[SchoolAdmissionResponse],
)
async def list_admissions(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.get_school_admissions(
        db,
        current_user.school_id,
    )


# =====================================================
# GET ONE ADMISSION
# =====================================================


@router.get(
    "/{admission_id}",
    response_model=SchoolAdmissionResponse,
)
async def get_admission(
    admission_id: UUID,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    admission = await service.get_by_id(
        db,
        admission_id,
    )

    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found.",
        )

    if admission.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access another school's admission.",
        )

    return admission


# =====================================================
# CREATE ADMISSION
# =====================================================


@router.post(
    "",
    response_model=SchoolAdmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admission(
    payload: SchoolAdmissionCreate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    try:
        return await service.create_admission(
            db,
            current_user.school_id,
            payload,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# =====================================================
# UPDATE ADMISSION
# =====================================================


@router.put(
    "/{admission_id}",
    response_model=SchoolAdmissionResponse,
)
async def update_admission(
    admission_id: UUID,
    payload: SchoolAdmissionUpdate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    admission = await service.get_by_id(
        db,
        admission_id,
    )

    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found.",
        )

    if admission.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot modify another school's admission.",
        )

    try:
        return await service.update_admission(
            db,
            admission,
            payload,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# =====================================================
# OPEN / CLOSE ADMISSION
# =====================================================


@router.patch(
    "/{admission_id}/status",
    response_model=SchoolAdmissionResponse,
)
async def update_admission_status(
    admission_id: UUID,
    payload: AdmissionStatusUpdate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    admission = await service.get_by_id(
        db,
        admission_id,
    )

    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found.",
        )

    if admission.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot modify another school's admission.",
        )

    return await service.update_status(
        db,
        admission,
        payload.is_open,
    )


# =====================================================
# UPLOAD BROCHURE
# =====================================================


@router.post(
    "/{admission_id}/brochure",
    response_model=SchoolAdmissionResponse,
)
async def upload_admission_brochure(
    admission_id: UUID,
    db: DBSession,
    current_user: RequireSchoolAdmin,
    file: UploadFile = File(...),
):
    admission = await service.get_by_id(
        db,
        admission_id,
    )

    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found.",
        )

    if admission.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot modify another school's admission.",
        )

    if admission.brochure_public_id:
        await cloudinary_service.delete_file(
            public_id=admission.brochure_public_id,
            resource_type="raw",
        )

    uploaded = await cloudinary_service.upload_file(
        file=file,
        folder=(f"school-directory/{current_user.school.slug}/admissions"),
        resource_type="raw",
    )

    return await service.update_brochure(
        db=db,
        admission=admission,
        brochure_url=uploaded["url"],
        brochure_public_id=uploaded["public_id"],
    )


# =====================================================
# DELETE BROCHURE
# =====================================================


@router.delete(
    "/{admission_id}/brochure",
    response_model=SchoolAdmissionResponse,
)
async def delete_admission_brochure(
    admission_id: UUID,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    admission = await service.get_by_id(
        db,
        admission_id,
    )

    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found.",
        )

    if admission.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot modify another school's admission.",
        )

    if admission.brochure_public_id:
        await cloudinary_service.delete_file(
            public_id=admission.brochure_public_id,
            resource_type="raw",
        )

    admission.brochure_url = None
    admission.brochure_public_id = None

    return await service.repo.save(
        db,
        admission,
    )


# =====================================================
# DELETE ADMISSION
# =====================================================


@router.delete(
    "/{admission_id}",
)
async def delete_admission(
    admission_id: UUID,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    admission = await service.get_by_id(
        db,
        admission_id,
    )

    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found.",
        )

    if admission.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete another school's admission.",
        )

    if admission.brochure_public_id:
        await cloudinary_service.delete_file(
            public_id=admission.brochure_public_id,
            resource_type="raw",
        )

    await service.delete_admission(
        db,
        admission,
    )

    return {
        "message": "Admission deleted successfully.",
    }
