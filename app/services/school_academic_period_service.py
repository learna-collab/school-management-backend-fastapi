from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_session import AcademicSession
from app.models.school_academic_period import SchoolAcademicPeriod
from app.models.terms import Term
from app.repositories.school_academic_period_repository import (
    SchoolAcademicPeriodRepository,
)


class SchoolAcademicPeriodService:
    def __init__(self):
        self.repository = SchoolAcademicPeriodRepository()

    async def get_options(self, db: AsyncSession):
        sessions_result = await db.execute(
            select(AcademicSession)
            .where(AcademicSession.is_active.is_(True))
            .order_by(AcademicSession.start_date.desc())
        )

        terms_result = await db.execute(
            select(Term).where(Term.is_active.is_(True)).order_by(Term.sort_order.asc())
        )

        sessions = sessions_result.scalars().all()
        terms = terms_result.scalars().all()

        return {
            "sessions": sessions,
            "terms": terms,
        }

    async def get_current(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        period = await self.repository.get_current(db, school_id)

        if not period:
            return None

        return {
            "session_id": str(period.session.id),
            "session_name": period.session.name,
            "term_id": str(period.term.id),
            "term_name": period.term.name,
        }

    async def update_current(
        self,
        db: AsyncSession,
        school_id: UUID,
        session_id: UUID,
        term_id: UUID,
    ):
        await self.repository.clear_current(db, school_id)

        period = SchoolAcademicPeriod(
            school_id=school_id,
            session_id=session_id,
            term_id=term_id,
            is_current=True,
        )

        await self.repository.create(db, period)
        await db.commit()

        # Reload with relationships eagerly loaded
        return await self.get_current(db, school_id)
