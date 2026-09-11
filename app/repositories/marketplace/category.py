from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketplace.category import MarketplaceCategory


class CategoryRepository:
    async def create(
        self,
        db: AsyncSession,
        category: MarketplaceCategory,
    ) -> MarketplaceCategory:
        db.add(category)
        await db.flush()
        return category

    async def save(
        self,
        db: AsyncSession,
        category: MarketplaceCategory,
    ) -> MarketplaceCategory:
        db.add(category)
        await db.flush()
        return category

    async def get_by_id(
        self,
        db: AsyncSession,
        category_id: UUID,
    ) -> MarketplaceCategory | None:
        result = await db.execute(
            select(MarketplaceCategory).where(MarketplaceCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str,
    ) -> MarketplaceCategory | None:
        result = await db.execute(
            select(MarketplaceCategory).where(MarketplaceCategory.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_active(
        self,
        db: AsyncSession,
    ) -> list[MarketplaceCategory]:
        result = await db.execute(
            select(MarketplaceCategory)
            .where(MarketplaceCategory.is_active.is_(True))
            .order_by(MarketplaceCategory.name.asc())
        )

        return list(result.scalars().all())

    async def list_all(
        self,
        db: AsyncSession,
    ) -> list[MarketplaceCategory]:
        result = await db.execute(
            select(MarketplaceCategory).order_by(MarketplaceCategory.name.asc())
        )

        return list(result.scalars().all())
