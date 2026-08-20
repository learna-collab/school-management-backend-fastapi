from datetime import date

from sqlalchemy import and_, or_, select

from app.models.school_admission import SchoolAdmission


class SchoolAdmissionRepository:
    async def create(
        self,
        db,
        admission: SchoolAdmission,
    ):
        db.add(admission)

        await db.commit()
        await db.refresh(admission)

        return admission

    async def get_by_id(
        self,
        db,
        admission_id,
    ):
        result = await db.execute(
            select(SchoolAdmission).where(
                SchoolAdmission.id == admission_id,
            ),
        )

        return result.scalar_one_or_none()

    async def get_school_admissions(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(SchoolAdmission)
            .where(
                SchoolAdmission.school_id == school_id,
            )
            .order_by(
                SchoolAdmission.application_deadline.asc().nullslast(),
                SchoolAdmission.created_at.desc(),
            ),
        )

        return result.scalars().all()

    async def get_open_school_admissions(
        self,
        db,
        school_id,
    ):
        today = date.today()

        result = await db.execute(
            select(SchoolAdmission)
            .where(
                SchoolAdmission.school_id == school_id,
                SchoolAdmission.is_open.is_(True),
                or_(
                    SchoolAdmission.application_deadline.is_(None),
                    SchoolAdmission.application_deadline >= today,
                ),
            )
            .order_by(
                SchoolAdmission.application_deadline.asc().nullslast(),
                SchoolAdmission.created_at.desc(),
            ),
        )

        return result.scalars().all()

    async def get_public_admission(
        self,
        db,
        school_id,
        admission_id,
    ):
        today = date.today()

        result = await db.execute(
            select(SchoolAdmission).where(
                SchoolAdmission.id == admission_id,
                SchoolAdmission.school_id == school_id,
                SchoolAdmission.is_open.is_(True),
                or_(
                    SchoolAdmission.application_deadline.is_(None),
                    SchoolAdmission.application_deadline >= today,
                ),
            ),
        )

        return result.scalar_one_or_none()

    async def get_all_open_admissions(
        self,
        db,
    ):
        today = date.today()

        result = await db.execute(
            select(SchoolAdmission)
            .where(
                SchoolAdmission.is_open.is_(True),
                or_(
                    SchoolAdmission.application_deadline.is_(None),
                    SchoolAdmission.application_deadline >= today,
                ),
            )
            .order_by(
                SchoolAdmission.application_deadline.asc().nullslast(),
                SchoolAdmission.created_at.desc(),
            ),
        )

        return result.scalars().all()

    async def exists_for_school_category(
        self,
        db,
        school_id,
        session_name,
        category,
        exclude_id=None,
    ):
        conditions = [
            SchoolAdmission.school_id == school_id,
            SchoolAdmission.session_name == session_name,
            SchoolAdmission.category == category,
        ]

        if exclude_id is not None:
            conditions.append(
                SchoolAdmission.id != exclude_id,
            )

        result = await db.execute(
            select(SchoolAdmission.id).where(
                and_(*conditions),
            ),
        )

        return result.scalar_one_or_none() is not None

    async def save(
        self,
        db,
        admission: SchoolAdmission,
    ):
        db.add(admission)

        await db.commit()
        await db.refresh(admission)

        return admission

    async def delete(
        self,
        db,
        admission: SchoolAdmission,
    ):
        await db.delete(admission)

        await db.commit()
