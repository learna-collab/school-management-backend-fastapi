from typing import Any, TypeVar
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)

class FinanceRepository:
    """School-scoped persistence primitives. Domain rules belong in services."""
    def __init__(self, model: type[ModelT]):
        self.model = model

    async def get(self, db: AsyncSession, school_id: UUID, row_id: UUID) -> ModelT | None:
        result = await db.execute(select(self.model).where(self.model.id == row_id, self.model.school_id == school_id))
        return result.scalar_one_or_none()

    async def list(self, db: AsyncSession, school_id: UUID, *, limit: int = 100, offset: int = 0, **filters: Any) -> list[ModelT]:
        stmt = select(self.model).where(self.model.school_id == school_id)
        for field, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field) == value)
        if hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())
        result = await db.execute(stmt.limit(limit).offset(offset))
        return list(result.scalars().all())

    async def add(self, db: AsyncSession, row: ModelT) -> ModelT:
        db.add(row)
        await db.flush()
        return row
