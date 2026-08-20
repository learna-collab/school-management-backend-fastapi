from app.models.school_admission import SchoolAdmission
from app.repositories.directory.admission_repository import (
    SchoolAdmissionRepository,
)


class SchoolAdmissionService:
    def __init__(self):
        self.repo = SchoolAdmissionRepository()

    async def create_admission(
        self,
        db,
        school_id,
        payload,
    ):
        exists = await self.repo.exists_for_school_category(
            db=db,
            school_id=school_id,
            session_name=payload.session_name,
            category=payload.category,
        )

        if exists:
            raise ValueError(
                "An admission for this session and category already exists.",
            )

        admission = SchoolAdmission(
            school_id=school_id,
            session_name=payload.session_name,
            title=payload.title,
            category=payload.category,
            description=payload.description,
            requirements=payload.requirements,
            application_fee=payload.application_fee,
            application_deadline=payload.application_deadline,
            application_url=(
                str(payload.application_url) if payload.application_url else None
            ),
            is_open=payload.is_open,
        )

        return await self.repo.create(
            db,
            admission,
        )

    async def get_school_admissions(
        self,
        db,
        school_id,
    ):
        return await self.repo.get_school_admissions(
            db,
            school_id,
        )

    async def get_open_school_admissions(
        self,
        db,
        school_id,
    ):
        return await self.repo.get_open_school_admissions(
            db,
            school_id,
        )

    async def get_public_admission(
        self,
        db,
        school_id,
        admission_id,
    ):
        return await self.repo.get_public_admission(
            db,
            school_id,
            admission_id,
        )

    async def get_all_open_admissions(
        self,
        db,
    ):
        return await self.repo.get_all_open_admissions(
            db,
        )

    async def get_by_id(
        self,
        db,
        admission_id,
    ):
        return await self.repo.get_by_id(
            db,
            admission_id,
        )

    async def update_admission(
        self,
        db,
        admission,
        payload,
    ):
        data = payload.model_dump(
            exclude_unset=True,
        )

        session_name = data.get(
            "session_name",
            admission.session_name,
        )

        category = data.get(
            "category",
            admission.category,
        )

        duplicate = await self.repo.exists_for_school_category(
            db=db,
            school_id=admission.school_id,
            session_name=session_name,
            category=category,
            exclude_id=admission.id,
        )

        if duplicate:
            raise ValueError(
                "An admission for this session and category already exists.",
            )

        if "application_url" in data:
            data["application_url"] = (
                str(data["application_url"]) if data["application_url"] else None
            )

        for field, value in data.items():
            setattr(
                admission,
                field,
                value,
            )

        return await self.repo.save(
            db,
            admission,
        )

    async def update_status(
        self,
        db,
        admission,
        is_open,
    ):
        admission.is_open = is_open

        return await self.repo.save(
            db,
            admission,
        )

    async def update_brochure(
        self,
        db,
        admission,
        brochure_url,
        brochure_public_id,
    ):
        admission.brochure_url = brochure_url
        admission.brochure_public_id = brochure_public_id

        return await self.repo.save(
            db,
            admission,
        )

    async def delete_admission(
        self,
        db,
        admission,
    ):
        await self.repo.delete(
            db,
            admission,
        )
