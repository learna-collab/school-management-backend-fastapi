import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.marketplace import (
    MarketplaceOrder,
)


class MarketplaceOrderRepository:
    @staticmethod
    async def get_customer_orders(
        db: AsyncSession,
        customer_id: uuid.UUID,
    ) -> list[MarketplaceOrder]:
        result = await db.execute(
            select(MarketplaceOrder)
            .where(MarketplaceOrder.customer_id == customer_id)
            .options(selectinload(MarketplaceOrder.items))
            .order_by(MarketplaceOrder.created_at.desc())
        )

        return list(result.scalars().all())

    @staticmethod
    async def get_customer_order(
        db: AsyncSession,
        customer_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> MarketplaceOrder | None:
        result = await db.execute(
            select(MarketplaceOrder)
            .where(
                MarketplaceOrder.id == order_id,
                MarketplaceOrder.customer_id == customer_id,
            )
            .options(selectinload(MarketplaceOrder.items))
        )

        return result.scalar_one_or_none()
