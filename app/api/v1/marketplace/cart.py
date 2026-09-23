from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DBSession
from app.schemas.marketplace.cart import (
    AddToCartRequest,
    CartResponse,
    UpdateCartItemRequest,
)
from app.services.marketplace.cart_service import CartService

router = APIRouter(
    prefix="/marketplace/cart",
    tags=["Marketplace Cart"],
)


@router.get(
    "",
    response_model=CartResponse,
)
async def get_cart(
    db: DBSession,
    current_user: CurrentUser,
):
    cart = await CartService.get_cart(
        db,
        current_user.id,
    )

    return _serialize_cart(cart)


@router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_cart(
    payload: AddToCartRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    cart = await CartService.add_item(
        db=db,
        customer_id=current_user.id,
        listing_id=payload.listing_id,
        quantity=payload.quantity,
    )

    return _serialize_cart(cart)


@router.patch(
    "/items/{item_id}",
    response_model=CartResponse,
)
async def update_cart_item(
    item_id: UUID,
    payload: UpdateCartItemRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    cart = await CartService.update_item(
        db=db,
        customer_id=current_user.id,
        item_id=item_id,
        quantity=payload.quantity,
    )

    return _serialize_cart(cart)


@router.delete(
    "/items/{item_id}",
    response_model=CartResponse,
)
async def remove_cart_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    cart = await CartService.remove_item(
        db=db,
        customer_id=current_user.id,
        item_id=item_id,
    )

    return _serialize_cart(cart)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_cart(
    db: DBSession,
    current_user: CurrentUser,
):
    await CartService.clear_cart(
        db,
        current_user.id,
    )


def _serialize_cart(cart):
    items = []
    total_amount = 0
    total_items = 0

    for item in cart.items:
        listing = item.listing

        unit_price = listing.price
        subtotal = unit_price * item.quantity

        items.append(
            {
                "id": item.id,
                "listing_id": listing.id,
                "quantity": item.quantity,
                "title": listing.title,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "currency": listing.currency,
            }
        )

        total_amount += subtotal
        total_items += item.quantity

    return {
        "id": cart.id,
        "customer_id": cart.customer_id,
        "items": items,
        "total_items": total_items,
        "total_amount": total_amount,
        "currency": "NGN",
    }
