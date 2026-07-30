from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_session import AcademicSession
from app.models.terms import Term
from app.repositories.super_admin_academic_repository import (
    SuperAdminAcademicRepository,
)


class SuperAdminAcademicService:
    def __init__(self):
        self.repository = SuperAdminAcademicRepository()

    # =========================
    # Sessions
    # =========================

    async def create_session(
        self,
        db: AsyncSession,
        name: str,
        start_date,
        end_date,
    ):
        session = AcademicSession(
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
        )

        await self.repository.create_session(db, session)
        await db.commit()
        return session

    async def list_sessions(self, db: AsyncSession):
        return await self.repository.list_sessions(db)

    async def update_session(
        self,
        db: AsyncSession,
        session_id: UUID,
        name: str,
        start_date,
        end_date,
    ):
        session = await self.repository.get_session(db, session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        session.name = name
        session.start_date = start_date
        session.end_date = end_date

        await db.commit()
        await db.refresh(session)

        return session

    async def set_session_active(
        self,
        db: AsyncSession,
        session_id: UUID,
        value: bool,
    ):
        session = await self.repository.get_session(db, session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        session.is_active = value

        await db.commit()
        await db.refresh(session)

        return session

    async def delete_session(
        self,
        db: AsyncSession,
        session_id: UUID,
    ):
        session = await self.repository.get_session(db, session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await self.repository.delete_session(db, session)
        await db.commit()

    # =========================
    # Terms
    # =========================

    async def create_term(
        self,
        db: AsyncSession,
        name: str,
        sort_order: int,
    ):
        term = Term(
            name=name,
            sort_order=sort_order,
            is_active=True,
        )

        await self.repository.create_term(db, term)
        await db.commit()

        return term

    async def list_terms(self, db: AsyncSession):
        return await self.repository.list_terms(db)

    async def update_term(
        self,
        db: AsyncSession,
        term_id: UUID,
        name: str,
        sort_order: int,
    ):
        term = await self.repository.get_term(db, term_id)

        if not term:
            raise HTTPException(status_code=404, detail="Term not found")

        term.name = name
        term.sort_order = sort_order

        await db.commit()
        await db.refresh(term)

        return term

    async def set_term_active(
        self,
        db: AsyncSession,
        term_id: UUID,
        value: bool,
    ):
        term = await self.repository.get_term(db, term_id)

        if not term:
            raise HTTPException(status_code=404, detail="Term not found")

        term.is_active = value

        await db.commit()
        await db.refresh(term)

        return term

    async def delete_term(
        self,
        db: AsyncSession,
        term_id: UUID,
    ):
        term = await self.repository.get_term(db, term_id)

        if not term:
            raise HTTPException(status_code=404, detail="Term not found")

        await self.repository.delete_term(db, term)
        await db.commit()
