from app.models.admission_enquiry import AdmissionEnquiry
from app.repositories.directory.admission_enquiry_repository import (
    AdmissionEnquiryRepository,
)


class AdmissionEnquiryService:
    def __init__(self):
        self.repo = AdmissionEnquiryRepository()

    async def get_enquiry_counts(
        self,
        db,
        school_id,
    ):
        return await self.repo.get_enquiry_counts(
            db,
            school_id,
        )

    async def create_enquiry(
        self,
        db,
        school_id,
        admission_id,
        payload,
    ):
        enquiry = AdmissionEnquiry(
            school_id=school_id,
            admission_id=admission_id,
            parent_name=payload.parent_name.strip(),
            email=(payload.email.strip() if payload.email else None),
            phone=payload.phone.strip(),
            student_name=(
                payload.student_name.strip() if payload.student_name else None
            ),
            student_class=(
                payload.student_class.strip() if payload.student_class else None
            ),
            message=(payload.message.strip() if payload.message else None),
        )

        return await self.repo.create(
            db,
            enquiry,
        )

    async def get_by_id(
        self,
        db,
        enquiry_id,
    ):
        return await self.repo.get_by_id(
            db,
            enquiry_id,
        )

    async def get_school_enquiries(
        self,
        db,
        school_id,
        status_filter=None,
    ):
        return await self.repo.get_school_enquiries(
            db,
            school_id,
            status_filter,
        )

    async def count_school_enquiries(
        self,
        db,
        school_id,
        status_filter=None,
    ):
        return await self.repo.count_school_enquiries(
            db,
            school_id,
            status_filter,
        )

    async def update_status(
        self,
        db,
        enquiry,
        status,
    ):
        enquiry.status = status

        return await self.repo.save(
            db,
            enquiry,
        )

    async def delete_enquiry(
        self,
        db,
        enquiry,
    ):
        await self.repo.delete(
            db,
            enquiry,
        )
