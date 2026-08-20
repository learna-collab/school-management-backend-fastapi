from app.models.school_facility import SchoolFacility
from app.repositories.directory.facility_repository import (
    SchoolFacilityRepository,
)


class SchoolFacilityService:
    def __init__(self):
        self.repo = SchoolFacilityRepository()

    async def list_school_facilities(
        self,
        db,
        school_id,
    ):
        return await self.repo.get_school_facilities(
            db,
            school_id,
        )

    async def create_facility(
        self,
        db,
        school_id,
        payload,
    ):
        facility = SchoolFacility(
            school_id=school_id,
            **payload.model_dump(),
        )

        return await self.repo.create(
            db,
            facility,
        )

    async def update_facility(
        self,
        db,
        facility,
        payload,
    ):
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(facility, field, value)

        return await self.repo.save(
            db,
            facility,
        )

    async def delete_facility(
        self,
        db,
        facility,
    ):
        await self.repo.delete(
            db,
            facility,
        )
