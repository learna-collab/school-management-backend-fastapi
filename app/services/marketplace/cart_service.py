import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.marketplace import (
    ListingStatus,
    MarketplaceCart,
    MarketplaceCartItem,
    MarketplaceListing,
)
from app.models.marketplace.vendor import VendorStatus
from app.repositories.marketplace.cart_repository import (
    MarketplaceCartRepository,
)


class CartService:
    @staticmethod
    async def get_cart(
        db: AsyncSession,
        customer_id: uuid.UUID,
    ) -> MarketplaceCart:
        cart = await MarketplaceCartRepository.get_or_create(
            db,
            customer_id,
        )

        await db.refresh(
            cart,
            attribute_names=["items"],
        )

        result = await db.execute(
            select(MarketplaceCart)
            .where(MarketplaceCart.id == cart.id)
            .options(
                selectinload(MarketplaceCart.items).selectinload(
                    MarketplaceCartItem.listing,
                ),
            ),
        )

        return result.scalar_one()

    @staticmethod
    async def add_item(
        db: AsyncSession,
        customer_id: uuid.UUID,
        listing_id: uuid.UUID,
        quantity: int,
    ) -> MarketplaceCart:
        if quantity < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be at least 1.",
            )

        listing_result = await db.execute(
            select(MarketplaceListing)
            .where(MarketplaceListing.id == listing_id)
            .options(selectinload(MarketplaceListing.vendor)),
        )

        listing = listing_result.scalar_one_or_none()

        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Listing not found.",
            )

        if listing.status != ListingStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Listing is not available.",
            )

        if (
            listing.vendor.status != VendorStatus.APPROVED
            or not listing.vendor.is_active
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor is not available.",
            )

        cart = await MarketplaceCartRepository.get_or_create(
            db,
            customer_id,
        )

        existing_item = await MarketplaceCartRepository.get_item(
            db,
            cart.id,
            listing_id,
        )

        if existing_item:
            existing_item.quantity += quantity
        else:
            db.add(
                MarketplaceCartItem(
                    cart_id=cart.id,
                    listing_id=listing_id,
                    quantity=quantity,
                ),
            )

        await db.commit()

        return await CartService.get_cart(
            db,
            customer_id,
        )

    @staticmethod
    async def update_item(
        db: AsyncSession,
        customer_id: uuid.UUID,
        item_id: uuid.UUID,
        quantity: int,
    ) -> MarketplaceCart:
        if quantity < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be at least 1.",
            )

        cart = await MarketplaceCartRepository.get_or_create(
            db,
            customer_id,
        )

        item = await MarketplaceCartRepository.get_item_by_id(
            db,
            cart.id,
            item_id,
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found.",
            )

        item.quantity = quantity

        await db.commit()

        return await CartService.get_cart(
            db,
            customer_id,
        )

    @staticmethod
    async def remove_item(
        db: AsyncSession,
        customer_id: uuid.UUID,
        item_id: uuid.UUID,
    ) -> MarketplaceCart:
        cart = await MarketplaceCartRepository.get_or_create(
            db,
            customer_id,
        )

        item = await MarketplaceCartRepository.get_item_by_id(
            db,
            cart.id,
            item_id,
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found.",
            )

        await MarketplaceCartRepository.delete_item(
            db,
            item,
        )

        await db.commit()

        return await CartService.get_cart(
            db,
            customer_id,
        )

    @staticmethod
    async def clear_cart(
        db: AsyncSession,
        customer_id: uuid.UUID,
    ) -> None:
        cart = await MarketplaceCartRepository.get_by_customer(
            db,
            customer_id,
        )

        if not cart:
            return

        await MarketplaceCartRepository.clear(
            db,
            cart,
        )

        (await db.commit(),)
