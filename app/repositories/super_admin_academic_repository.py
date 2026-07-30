from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_session import AcademicSession
from app.models.terms import Term


class SuperAdminAcademicRepository:
    # =========================
    # Sessions
    # =========================

    async def create_session(
        self,
        db: AsyncSession,
        session: AcademicSession,
    ):
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    async def list_sessions(self, db: AsyncSession):
        result = await db.execute(
            select(AcademicSession).order_by(AcademicSession.start_date.desc())
        )
        return result.scalars().all()

    async def get_session(
        self,
        db: AsyncSession,
        session_id: UUID,
    ):
        return await db.get(AcademicSession, session_id)

    async def delete_session(
        self,
        db: AsyncSession,
        session: AcademicSession,
    ):
        await db.delete(session)

    # =========================
    # Terms
    # =========================

    async def create_term(
        self,
        db: AsyncSession,
        term: Term,
    ):
        db.add(term)
        await db.flush()
        await db.refresh(term)
        return term

    async def list_terms(self, db: AsyncSession):
        result = await db.execute(select(Term).order_by(Term.sort_order.asc()))
        return result.scalars().all()

    async def get_term(
        self,
        db: AsyncSession,
        term_id: UUID,
    ):
        return await db.get(Term, term_id)

    async def delete_term(
        self,
        db: AsyncSession,
        term: Term,
    ):
        await db.delete(term)
