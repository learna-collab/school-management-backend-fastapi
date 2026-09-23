from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckoutOrderResponse(BaseModel):
    id: UUID
    order_number: str
    vendor_id: UUID
    total_amount: Decimal
    commission_amount: Decimal
    vendor_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class CheckoutResponse(BaseModel):
    id: UUID
    checkout_number: str
    customer_id: UUID
    total_amount: Decimal
    currency: str
    status: str

    orders: list[CheckoutOrderResponse]

    model_config = ConfigDict(from_attributes=True)


class CheckoutInitializeResponse(BaseModel):
    checkout_id: UUID
    checkout_number: str
    reference: str
    authorization_url: str
    access_code: str
