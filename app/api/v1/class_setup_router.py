from fastapi import APIRouter, Request

from app.core.deps import DBSession, RequireSchoolAdmin
from app.schemas.academic_setup import (
    ConfigureAcademicSetupRequest,
)
from app.services.setup_service import (
    AcademicSetupService,
)

router = APIRouter(
    prefix="/academic-setup",
    tags=["Academic Setup"],
)

service = AcademicSetupService()


@router.get("/templates")
async def get_templates(
    db: DBSession,
    _: RequireSchoolAdmin,
):
    return await service.get_templates(db)


@router.post("/configure")
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
