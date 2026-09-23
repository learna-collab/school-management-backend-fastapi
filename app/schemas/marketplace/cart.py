from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AddToCartRequest(BaseModel):
    listing_id: UUID
    quantity: int = Field(default=1, ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemResponse(BaseModel):
    id: UUID
    listing_id: UUID
    quantity: int

    title: str
    unit_price: Decimal
    subtotal: Decimal
    currency: str

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    id: UUID
    customer_id: UUID

    items: list[CartItemResponse]

    total_items: int
    total_amount: Decimal
    currency: str = "NGN"

    model_config = ConfigDict(from_attributes=True)
