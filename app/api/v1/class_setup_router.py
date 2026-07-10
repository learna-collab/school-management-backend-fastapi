from fastapi import APIRouter

from app.core.deps import DBSession, RequireSchoolAdmin
from app.schemas.academic_setup import (
    AcademicSetupSummaryResponse,
    AcademicTemplateResponse,
    AssignSubjectsRequest,
    ConfigureAcademicSetupRequest,
    CreateClassRequest,
    CreateSubjectRequest,
    SchoolAcademicSetupResponse,
    UpdateClassRequest,
    UpdateSubjectRequest,
)
from app.services.setup_service import AcademicSetupService

router = APIRouter(
    prefix="/academic-setup",
    tags=["Academic Setup"],
)

service = AcademicSetupService()

# ==========================================================
# TEMPLATE
# ==========================================================


@router.get(
    "/templates",
    response_model=list[AcademicTemplateResponse],
)
async def get_templates(
    db: DBSession,
    _: RequireSchoolAdmin,
):
    return await service.get_templates(db)


# ==========================================================
# SCHOOL SETUP
# ==========================================================


@router.get(
    "/school",
    response_model=SchoolAcademicSetupResponse,
)
async def get_school_setup(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.get_school_setup(
        db=db,
        school_id=current_user.school_id,
    )


@router.post(
    "/configure",
    response_model=AcademicSetupSummaryResponse,
)
async def configure_school(
    payload: ConfigureAcademicSetupRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.configure(
        db=db,
        payload=payload,
        school_id=current_user.school_id,
    )


@router.put(
    "",
    response_model=AcademicSetupSummaryResponse,
)
async def update_school_setup(
    payload: ConfigureAcademicSetupRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.update_setup(
        db=db,
        payload=payload,
        school_id=current_user.school_id,
    )


# ==========================================================
# CLASS CRUD
# ==========================================================


@router.post("/classes")
async def create_class(
    payload: CreateClassRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.create_class(
        db=db,
        school_id=current_user.school_id,
        payload=payload,
    )


@router.patch("/classes/{class_id}")
async def update_class(
    class_id,
    payload: UpdateClassRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.update_class(
        db=db,
        school_id=current_user.school_id,
        class_id=class_id,
        payload=payload,
    )


@router.delete("/classes/{class_id}")
async def delete_class(
    class_id,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.delete_class(
        db=db,
        school_id=current_user.school_id,
        class_id=class_id,
    )


# ==========================================================
# SUBJECT CRUD
# ==========================================================


@router.post("/subjects")
async def create_subject(
    payload: CreateSubjectRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.create_subject(
        db=db,
        school_id=current_user.school_id,
        payload=payload,
    )


@router.patch("/subjects/{subject_id}")
async def update_subject(
    subject_id,
    payload: UpdateSubjectRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.update_subject(
        db=db,
        school_id=current_user.school_id,
        subject_id=subject_id,
        payload=payload,
    )


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.delete_subject(
        db=db,
        school_id=current_user.school_id,
        subject_id=subject_id,
    )


# ==========================================================
# CLASS SUBJECTS
# ==========================================================


@router.put("/classes/{class_id}/subjects")
async def assign_subjects(
    class_id,
    payload: AssignSubjectsRequest,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.assign_subjects(
        db=db,
        school_id=current_user.school_id,
        class_id=class_id,
        payload=payload,
    )
