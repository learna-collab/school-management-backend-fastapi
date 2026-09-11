from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketplace.vendor import Vendor, VendorStatus


class VendorRepository:
    async def create(
        self,
        db: AsyncSession,
        vendor: Vendor,
    ) -> Vendor:
        db.add(vendor)
        await db.commit()
        await db.refresh(vendor)
        return vendor

    async def save(
        self,
        db: AsyncSession,
        vendor: Vendor,
    ) -> Vendor:
        db.add(vendor)
        await db.commit()
        await db.refresh(vendor)
        return vendor

    async def get_by_id(
        self,
        db: AsyncSession,
        vendor_id: UUID,
    ) -> Vendor | None:
        result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> Vendor | None:
        result = await db.execute(select(Vendor).where(Vendor.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str,
    ) -> Vendor | None:
        result = await db.execute(select(Vendor).where(Vendor.slug == slug))
        return result.scalar_one_or_none()

    async def slug_exists(
        self,
        db: AsyncSession,
        slug: str,
    ) -> bool:
        result = await db.execute(select(Vendor.id).where(Vendor.slug == slug))
        return result.scalar_one_or_none() is not None

    async def list_pending(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Vendor], int]:
        total = await db.scalar(
            select(func.count())
            .select_from(Vendor)
            .where(Vendor.status == VendorStatus.PENDING)
        )

        result = await db.execute(
            select(Vendor)
            .where(Vendor.status == VendorStatus.PENDING)
            .order_by(Vendor.created_at.asc())
            .offset(offset)
            .limit(limit)
        )

        return list(result.scalars().all()), total or 0

    async def list_all(
        self,
        db: AsyncSession,
        status: VendorStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Vendor], int]:
        query = select(Vendor)
        count_query = select(func.count()).select_from(Vendor)

        if status:
            query = query.where(Vendor.status == status)
            count_query = count_query.where(Vendor.status == status)

        total = await db.scalar(count_query)

        result = await db.execute(
            query.order_by(Vendor.created_at.desc()).offset(offset).limit(limit)
        )

        return list(result.scalars().all()), total or 0
