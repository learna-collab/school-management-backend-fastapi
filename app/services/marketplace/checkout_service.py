import uuid
from collections import defaultdict
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.marketplace import (
    ListingStatus,
    MarketplaceCartItem,
    MarketplaceCheckout,
    MarketplaceListing,
    MarketplaceOrder,
    MarketplaceOrderItem,
    PhysicalProduct,
)
from app.models.marketplace.marketplace_checkout import (
    CheckoutStatus,
)
from app.models.marketplace.marketplace_order import (
    OrderStatus,
)
from app.models.marketplace.vendor import (
    VendorStatus,
)
from app.repositories.marketplace.cart_repository import (
    MarketplaceCartRepository,
)

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


class CheckoutService:
    COMMISSION_RATE = Decimal("0.10")

    @staticmethod
    def _checkout_number() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")

        return f"CHK-{timestamp}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def _order_number() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")

        return f"ORD-{timestamp}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    async def create_checkout(
        db: AsyncSession,
        customer_id: uuid.UUID,
    ) -> MarketplaceCheckout:
        # ---------------------------------------------------------
        # Load the customer's cart.
        # ---------------------------------------------------------
        cart = await MarketplaceCartRepository.get_by_customer(
            db=db,
            customer_id=customer_id,
        )

        if not cart:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your cart is empty.",
            )

        # ---------------------------------------------------------
        # Lock the cart items for checkout.
        #
        # The repository loads:
        # CartItem -> Listing -> Vendor
        #
        # This prevents another checkout transaction from
        # modifying the same cart items while we process them.
        # ---------------------------------------------------------
        cart_items = await MarketplaceCartRepository.get_items_for_checkout(
            db=db,
            cart_id=cart.id,
        )

        if not cart_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your cart is empty.",
            )

        grouped_items: dict[
            uuid.UUID,
            list[
                tuple[
                    MarketplaceCartItem,
                    MarketplaceListing,
                    Decimal,
                ]
            ],
        ] = defaultdict(list)

        checkout_total = Decimal("0.00")

        # ---------------------------------------------------------
        # Validate cart items and reserve inventory.
        # ---------------------------------------------------------
        try:
            for cart_item in cart_items:
                listing = cart_item.listing

                # -------------------------------------------------
                # Listing must exist.
                # -------------------------------------------------
                if not listing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=("One of the products in your cart no longer exists."),
                    )

                # -------------------------------------------------
                # Listing must be active.
                # -------------------------------------------------
                if listing.status != ListingStatus.ACTIVE:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(f'"{listing.title}" is no longer available.'),
                    )

                # -------------------------------------------------
                # Vendor must exist.
                # -------------------------------------------------
                vendor = listing.vendor

                if not vendor:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(f'"{listing.title}" has no valid vendor.'),
                    )

                # -------------------------------------------------
                # Vendor must be approved and active.
                # -------------------------------------------------
                if vendor.status != VendorStatus.APPROVED or not vendor.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(f'"{listing.title}" cannot currently be purchased.'),
                    )

                # -------------------------------------------------
                # Quantity must be valid.
                # -------------------------------------------------
                if cart_item.quantity < 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid cart quantity.",
                    )

                # -------------------------------------------------
                # Reserve stock for physical products.
                # -------------------------------------------------
                if listing.listing_type.name == "PHYSICAL":
                    stock_result = await db.execute(
                        select(PhysicalProduct)
                        .where(PhysicalProduct.listing_id == listing.id)
                        .with_for_update()
                    )

                    physical = stock_result.scalar_one_or_none()

                    if not physical:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(f'"{listing.title}" has no inventory record.'),
                        )

                    if physical.stock_quantity < cart_item.quantity:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"Insufficient stock for "
                                f'"{listing.title}". '
                                f"Available: "
                                f"{physical.stock_quantity}."
                            ),
                        )

                    physical.stock_quantity -= cart_item.quantity

                # -------------------------------------------------
                # Calculate frozen checkout pricing.
                # -------------------------------------------------
                unit_price = money(listing.price)

                subtotal = money(unit_price * cart_item.quantity)

                checkout_total += subtotal

                grouped_items[vendor.id].append(
                    (
                        cart_item,
                        listing,
                        subtotal,
                    )
                )

            # -----------------------------------------------------
            # Normalize total.
            # -----------------------------------------------------
            checkout_total = money(checkout_total)

            if checkout_total <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=("Checkout amount must be greater than zero."),
                )

            # -----------------------------------------------------
            # Create ONE marketplace checkout.
            # -----------------------------------------------------
            checkout = MarketplaceCheckout(
                customer_id=customer_id,
                checkout_number=(CheckoutService._checkout_number()),
                total_amount=checkout_total,
                currency="NGN",
                status=CheckoutStatus.PENDING,
            )

            db.add(checkout)

            await db.flush()

            # -----------------------------------------------------
            # Create ONE order for each vendor.
            # -----------------------------------------------------
            for vendor_id, items in grouped_items.items():
                vendor_total = money(sum(subtotal for _, _, subtotal in items))

                commission_amount = money(
                    vendor_total * CheckoutService.COMMISSION_RATE
                )

                vendor_amount = money(vendor_total - commission_amount)

                order = MarketplaceOrder(
                    checkout_id=checkout.id,
                    customer_id=customer_id,
                    vendor_id=vendor_id,
                    order_number=(CheckoutService._order_number()),
                    total_amount=vendor_total,
                    commission_amount=commission_amount,
                    vendor_amount=vendor_amount,
                    status=OrderStatus.PENDING,
                    delivery_confirmed=False,
                    released=False,
                )

                db.add(order)

                await db.flush()

                # -------------------------------------------------
                # Create frozen order items.
                # -------------------------------------------------
                for (
                    cart_item,
                    listing,
                    subtotal,
                ) in items:
                    order_item = MarketplaceOrderItem(
                        order_id=order.id,
                        listing_id=listing.id,
                        title=listing.title,
                        quantity=cart_item.quantity,
                        unit_price=money(listing.price),
                        subtotal=subtotal,
                    )

                    db.add(order_item)

            # -----------------------------------------------------
            # Clear the cart.
            #
            # The purchased information has already been frozen
            # into MarketplaceOrderItem records.
            # -----------------------------------------------------
            for item in cart_items:
                await db.delete(item)

            # -----------------------------------------------------
            # Commit everything atomically:
            #
            # - stock reservation
            # - checkout
            # - vendor orders
            # - order items
            # - cart removal
            # -----------------------------------------------------
            await db.commit()

        except Exception:
            # -----------------------------------------------------
            # If anything fails before commit, rollback the
            # transaction so reserved stock and created records
            # are not partially persisted.
            # -----------------------------------------------------
            await db.rollback()
            raise

        # ---------------------------------------------------------
        # Reload checkout with its vendor orders.
        # ---------------------------------------------------------
        result = await db.execute(
            select(MarketplaceCheckout)
            .where(MarketplaceCheckout.id == checkout.id)
            .options(selectinload(MarketplaceCheckout.orders))
        )

        return result.scalar_one()

    @staticmethod
    async def restore_checkout_stock(
        db: AsyncSession,
        checkout_id: uuid.UUID,
    ) -> None:
        # ---------------------------------------------------------
        # Load checkout and its order items while locking checkout.
        # ---------------------------------------------------------
        result = await db.execute(
            select(MarketplaceCheckout)
            .where(MarketplaceCheckout.id == checkout_id)
            .options(
                selectinload(MarketplaceCheckout.orders).selectinload(
                    MarketplaceOrder.items
                )
            )
            .with_for_update()
        )

        checkout = result.scalar_one_or_none()

        if not checkout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checkout not found.",
            )

        # ---------------------------------------------------------
        # Stock has already been restored.
        # ---------------------------------------------------------
        if checkout.stock_restored:
            return

        # ---------------------------------------------------------
        # Never restore stock for a successful payment.
        # ---------------------------------------------------------
        if checkout.status == CheckoutStatus.PAID:
            return

        # ---------------------------------------------------------
        # Restore stock for physical products.
        # ---------------------------------------------------------
        for order in checkout.orders:
            for order_item in order.items:
                result = await db.execute(
                    select(PhysicalProduct)
                    .where(PhysicalProduct.listing_id == order_item.listing_id)
                    .with_for_update()
                )

                physical_product = result.scalar_one_or_none()

                if physical_product:
                    physical_product.stock_quantity += order_item.quantity

        # ---------------------------------------------------------
        # Mark stock as restored.
        #
        # Caller controls the transaction/commit.
        # ---------------------------------------------------------
        checkout.stock_restored = True
