import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MarketplaceOrderItemResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    title: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class MarketplaceOrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    vendor_id: uuid.UUID
    checkout_id: uuid.UUID | None

    total_amount: Decimal
    commission_amount: Decimal
    vendor_amount: Decimal

    status: str
    delivery_confirmed: bool
    released: bool

    created_at: datetime
    updated_at: datetime

    items: list[MarketplaceOrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class MarketplaceOrderListResponse(BaseModel):
    orders: list[MarketplaceOrderResponse]
    total: int
