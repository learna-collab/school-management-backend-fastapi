from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.marketplace.listing import (
    ListingStatus,
    ListingType,
    MarketplaceListing,
)


class ListingRepository:
    def _listing_options(self):
        return (
            selectinload(MarketplaceListing.vendor),
            selectinload(MarketplaceListing.category),
            selectinload(MarketplaceListing.images),
            selectinload(MarketplaceListing.physical),
            selectinload(MarketplaceListing.service),
            selectinload(MarketplaceListing.digital),
        )

    async def create(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
    ) -> MarketplaceListing:
        db.add(listing)
        await db.flush()

        result = await db.execute(
            select(MarketplaceListing)
            .options(*self._listing_options())
            .where(MarketplaceListing.id == listing.id)
        )

        return result.scalar_one()

    async def save(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
    ) -> MarketplaceListing:
        db.add(listing)
        await db.flush()

        result = await db.execute(
            select(MarketplaceListing)
            .options(*self._listing_options())
            .where(MarketplaceListing.id == listing.id)
        )

        return result.scalar_one()

    async def get_by_id(
        self,
        db: AsyncSession,
        listing_id: UUID,
    ) -> MarketplaceListing | None:
        result = await db.execute(
            select(MarketplaceListing)
            .options(*self._listing_options())
            .where(MarketplaceListing.id == listing_id)
        )

        return result.scalar_one_or_none()

    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str,
    ) -> MarketplaceListing | None:
        result = await db.execute(
            select(MarketplaceListing)
            .options(*self._listing_options())
            .where(MarketplaceListing.slug == slug)
        )

        return result.scalar_one_or_none()

    async def slug_exists(
        self,
        db: AsyncSession,
        slug: str,
    ) -> bool:
        result = await db.execute(
            select(MarketplaceListing.id).where(MarketplaceListing.slug == slug)
        )

        return result.scalar_one_or_none() is not None

    async def get_vendor_listings(
        self,
        db: AsyncSession,
        vendor_id: UUID,
    ) -> list[MarketplaceListing]:
        result = await db.execute(
            select(MarketplaceListing)
            .options(*self._listing_options())
            .where(MarketplaceListing.vendor_id == vendor_id)
            .order_by(MarketplaceListing.created_at.desc())
        )

        return list(result.scalars().all())

    async def get_public_listings(
        self,
        db: AsyncSession,
        listing_type: ListingType | None = None,
        category_id: UUID | None = None,
    ) -> list[MarketplaceListing]:
        query = (
            select(MarketplaceListing)
            .options(*self._listing_options())
            .where(MarketplaceListing.status == ListingStatus.ACTIVE)
        )

        if listing_type:
            query = query.where(MarketplaceListing.listing_type == listing_type)

        if category_id:
            query = query.where(MarketplaceListing.category_id == category_id)

        query = query.order_by(MarketplaceListing.created_at.desc())

        result = await db.execute(query)

        return list(result.scalars().all())

    async def get_vendor_public_listings(
        self,
        db: AsyncSession,
        vendor_id: UUID,
    ) -> list[MarketplaceListing]:
        result = await db.execute(
            select(MarketplaceListing)
            .options(*self._listing_options())
            .where(
                MarketplaceListing.vendor_id == vendor_id,
                MarketplaceListing.status == ListingStatus.ACTIVE,
            )
            .order_by(MarketplaceListing.created_at.desc())
        )

        return list(result.scalars().all())
