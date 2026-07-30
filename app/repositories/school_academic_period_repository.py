from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.school_academic_period import SchoolAcademicPeriod


class SchoolAcademicPeriodRepository:
    async def get_current(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        result = await db.execute(
            select(SchoolAcademicPeriod)
            .options(
                selectinload(SchoolAcademicPeriod.session),
                selectinload(SchoolAcademicPeriod.term),
            )
            .where(
                SchoolAcademicPeriod.school_id == school_id,
                SchoolAcademicPeriod.is_current.is_(True),
            )
        )

        return result.scalar_one_or_none()

    async def clear_current(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        await db.execute(
            update(SchoolAcademicPeriod)
            .where(SchoolAcademicPeriod.school_id == school_id)
            .values(is_current=False)
        )

    async def create(
        self,
        db: AsyncSession,
        period: SchoolAcademicPeriod,
    ):
        db.add(period)

        await db.flush()
        await db.refresh(period)

        # Reload with relationships eagerly loaded
        result = await db.execute(
            select(SchoolAcademicPeriod)
            .options(
                selectinload(SchoolAcademicPeriod.session),
                selectinload(SchoolAcademicPeriod.term),
            )
            .where(SchoolAcademicPeriod.id == period.id)
        )

        return result.scalar_one()
