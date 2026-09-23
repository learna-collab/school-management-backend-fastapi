import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.marketplace.order_repository import (
    MarketplaceOrderRepository,
)


class MarketplaceOrderService:
    @staticmethod
    async def get_customer_orders(
        db: AsyncSession,
        customer_id: uuid.UUID,
    ):
        return await MarketplaceOrderRepository.get_customer_orders(
            db=db,
            customer_id=customer_id,
        )

    @staticmethod
    async def get_customer_order(
        db: AsyncSession,
        customer_id: uuid.UUID,
        order_id: uuid.UUID,
    ):
        order = await MarketplaceOrderRepository.get_customer_order(
            db=db,
            customer_id=customer_id,
            order_id=order_id,
        )

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found.",
            )

        return order
