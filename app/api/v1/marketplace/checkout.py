from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DBSession
from app.models.marketplace import MarketplaceCheckout
from app.schemas.marketplace.checkout import CheckoutResponse
from app.services.marketplace.checkout_service import CheckoutService

router = APIRouter(
    prefix="/marketplace/checkout",
    tags=["Marketplace Checkout"],
)


@router.post(
    "",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout(
    db: DBSession,
    current_user: CurrentUser,
):
    checkout = await CheckoutService.create_checkout(
        db=db,
        customer_id=current_user.id,
    )

    return {
        "id": checkout.id,
        "checkout_number": checkout.checkout_number,
        "customer_id": checkout.customer_id,
        "total_amount": checkout.total_amount,
        "currency": checkout.currency,
        "status": checkout.status.value
        if hasattr(checkout.status, "value")
        else checkout.status,
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "vendor_id": order.vendor_id,
                "total_amount": order.total_amount,
                "commission_amount": order.commission_amount,
                "vendor_amount": order.vendor_amount,
            }
            for order in checkout.orders
        ],
    }


@router.get(
    "/{checkout_id}",
    response_model=CheckoutResponse,
)
async def get_checkout(
    checkout_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(MarketplaceCheckout)
        .where(
            MarketplaceCheckout.id == checkout_id,
            MarketplaceCheckout.customer_id == current_user.id,
        )
        .options(selectinload(MarketplaceCheckout.orders)),
    )

    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout not found.",
        )

    return {
        "id": checkout.id,
        "checkout_number": checkout.checkout_number,
        "customer_id": checkout.customer_id,
        "total_amount": checkout.total_amount,
        "currency": checkout.currency,
        "status": checkout.status.value
        if hasattr(checkout.status, "value")
        else checkout.status,
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "vendor_id": order.vendor_id,
                "total_amount": order.total_amount,
                "commission_amount": order.commission_amount,
                "vendor_amount": order.vendor_amount,
            }
            for order in checkout.orders
        ],
    }
