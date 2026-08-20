from app.schemas.directory.facility import (
    SchoolFacilityCreate,
    SchoolFacilityUpdate,
)
from fastapi import APIRouter, HTTPException

from app.core.deps import DBSession, RequireSchoolAdmin
from app.services.directory.facility_service import (
    SchoolFacilityService,
)

router = APIRouter(
    prefix="/school-admin/directory/facilities",
    tags=["School Admin Facilities"],
)

service = SchoolFacilityService()


@router.get("")
async def list_facilities(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.list_school_facilities(
        db,
        current_user.school_id,
    )


@router.post("")
async def create_facility(
    payload: SchoolFacilityCreate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.create_facility(
        db,
        current_user.school_id,
        payload,
    )


@router.put("/{facility_id}")
async def update_facility(
    facility_id,
    payload: SchoolFacilityUpdate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    facility = await service.repo.get_by_id(
        db,
        facility_id,
    )

    if not facility or facility.school_id != current_user.school_id:
        raise HTTPException(404, "Facility not found")

    return await service.update_facility(
        db,
        facility,
        payload,
    )


@router.delete("/{facility_id}")
async def delete_facility(
    facility_id,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    facility = await service.repo.get_by_id(
        db,
        facility_id,
    )

    if not facility or facility.school_id != current_user.school_id:
        raise HTTPException(404, "Facility not found")

    await service.delete_facility(
        db,
        facility,
    )

    return {"message": "Facility deleted"}
