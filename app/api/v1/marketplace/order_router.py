from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DBSession
from app.schemas.marketplace.order import (
    MarketplaceOrderListResponse,
    MarketplaceOrderResponse,
)
from app.services.marketplace.order_service import (
    MarketplaceOrderService,
)

router = APIRouter(
    prefix="/marketplace/orders",
    tags=["Marketplace Orders"],
)


@router.get(
    "",
    response_model=MarketplaceOrderListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_orders(
    db: DBSession,
    current_user: CurrentUser,
):
    orders = await MarketplaceOrderService.get_customer_orders(
        db=db,
        customer_id=current_user.id,
    )

    return {
        "orders": orders,
        "total": len(orders),
    }


@router.get(
    "/{order_id}",
    response_model=MarketplaceOrderResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_order(
    order_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    return await MarketplaceOrderService.get_customer_order(
        db=db,
        customer_id=current_user.id,
        order_id=order_id,
    )
