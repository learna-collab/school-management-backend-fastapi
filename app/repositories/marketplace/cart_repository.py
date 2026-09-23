import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.marketplace import (
    MarketplaceCart,
    MarketplaceCartItem,
    MarketplaceListing,
)


class MarketplaceCartRepository:
    @staticmethod
    async def get_by_customer(
        db: AsyncSession,
        customer_id: uuid.UUID,
    ) -> MarketplaceCart | None:
        result = await db.execute(
            select(MarketplaceCart)
            .where(MarketplaceCart.customer_id == customer_id)
            .options(
                selectinload(MarketplaceCart.items).selectinload(
                    MarketplaceCartItem.listing
                )
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create(
        db: AsyncSession,
        customer_id: uuid.UUID,
    ) -> MarketplaceCart:
        cart = await MarketplaceCartRepository.get_by_customer(
            db=db,
            customer_id=customer_id,
        )

        if cart:
            return cart

        cart = MarketplaceCart(
            customer_id=customer_id,
        )

        db.add(cart)

        await db.flush()

        return cart

    @staticmethod
    async def get_item(
        db: AsyncSession,
        cart_id: uuid.UUID,
        listing_id: uuid.UUID,
    ) -> MarketplaceCartItem | None:
        result = await db.execute(
            select(MarketplaceCartItem).where(
                MarketplaceCartItem.cart_id == cart_id,
                MarketplaceCartItem.listing_id == listing_id,
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_item_by_id(
        db: AsyncSession,
        cart_id: uuid.UUID,
        item_id: uuid.UUID,
    ) -> MarketplaceCartItem | None:
        result = await db.execute(
            select(MarketplaceCartItem).where(
                MarketplaceCartItem.id == item_id,
                MarketplaceCartItem.cart_id == cart_id,
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_items_for_checkout(
        db: AsyncSession,
        cart_id: uuid.UUID,
    ) -> list[MarketplaceCartItem]:
        result = await db.execute(
            select(MarketplaceCartItem)
            .where(MarketplaceCartItem.cart_id == cart_id)
            .options(
                selectinload(MarketplaceCartItem.listing).selectinload(
                    MarketplaceListing.vendor
                )
            )
            .with_for_update()
        )

        return list(result.scalars().all())

    @staticmethod
    async def delete_item(
        db: AsyncSession,
        item: MarketplaceCartItem,
    ) -> None:
        await db.delete(item)

    @staticmethod
    async def clear(
        db: AsyncSession,
        cart: MarketplaceCart,
    ) -> None:
        for item in list(cart.items):
            await db.delete(item)

        await db.flush()
