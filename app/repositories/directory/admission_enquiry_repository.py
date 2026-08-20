from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.admission_enquiry import (
    AdmissionEnquiry,
    AdmissionEnquiryStatus,
)


class AdmissionEnquiryRepository:
    async def get_enquiry_counts(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(
                AdmissionEnquiry.status,
                func.count(AdmissionEnquiry.id),
            )
            .where(
                AdmissionEnquiry.school_id == school_id,
            )
            .group_by(
                AdmissionEnquiry.status,
            ),
        )

        rows = result.all()

        counts = {status.value: 0 for status in AdmissionEnquiryStatus}

        for enquiry_status, count in rows:
            counts[enquiry_status.value] = count

        counts["TOTAL"] = sum(counts.values())

        return counts

    async def create(
        self,
        db,
        enquiry: AdmissionEnquiry,
    ):
        db.add(enquiry)

        await db.commit()
        await db.refresh(enquiry)

        return enquiry

    async def get_by_id(
        self,
        db,
        enquiry_id,
    ):
        result = await db.execute(
            select(AdmissionEnquiry)
            .where(
                AdmissionEnquiry.id == enquiry_id,
            )
            .options(
                selectinload(
                    AdmissionEnquiry.admission,
                ),
            ),
        )

        return result.scalar_one_or_none()

    async def get_school_enquiries(
        self,
        db,
        school_id,
        status_filter=None,
    ):
        query = (
            select(AdmissionEnquiry)
            .where(
                AdmissionEnquiry.school_id == school_id,
            )
            .options(
                selectinload(
                    AdmissionEnquiry.admission,
                ),
            )
            .order_by(
                AdmissionEnquiry.created_at.desc(),
            )
        )

        if status_filter:
            query = query.where(
                AdmissionEnquiry.status == status_filter,
            )

        result = await db.execute(query)

        return result.scalars().all()

    async def count_school_enquiries(
        self,
        db,
        school_id,
        status_filter=None,
    ):
        query = select(
            func.count(AdmissionEnquiry.id),
        ).where(
            AdmissionEnquiry.school_id == school_id,
        )

        if status_filter:
            query = query.where(
                AdmissionEnquiry.status == status_filter,
            )

        result = await db.execute(query)

        return result.scalar_one()

    async def save(
        self,
        db,
        enquiry: AdmissionEnquiry,
    ):
        db.add(enquiry)

        await db.commit()
        await db.refresh(enquiry)

        return enquiry

    async def delete(
        self,
        db,
        enquiry: AdmissionEnquiry,
    ):
        await db.delete(enquiry)

        await db.commit()
