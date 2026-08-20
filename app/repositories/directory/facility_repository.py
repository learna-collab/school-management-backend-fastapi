from sqlalchemy import select

from app.models.school_facility import SchoolFacility


class SchoolFacilityRepository:
    async def get_school_facilities(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(SchoolFacility)
            .where(SchoolFacility.school_id == school_id)
            .order_by(SchoolFacility.name)
        )

        return result.scalars().all()

    async def get_by_id(
        self,
        db,
        facility_id,
    ):
        result = await db.execute(
            select(SchoolFacility).where(SchoolFacility.id == facility_id)
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        db,
        facility,
    ):
        db.add(facility)

        await db.commit()

        await db.refresh(facility)

        return facility

    async def save(
        self,
        db,
        facility,
    ):
        db.add(facility)

        await db.commit()

        await db.refresh(facility)

        return facility

    async def delete(
        self,
        db,
        facility,
    ):
        await db.delete(facility)

        await db.commit()
