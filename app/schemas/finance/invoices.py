from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

class InvoiceLineCreate(BaseModel):
    description: str = Field(min_length=2, max_length=255)
    quantity: int = Field(default=1, ge=1, le=10000)
    unit_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    fee_category_id: UUID | None = None

class InvoiceCreate(BaseModel):
    student_id: UUID
    session_id: UUID
    term_id: UUID
    invoice_number: str = Field(min_length=2, max_length=60)
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)
    note: str | None = None

class InvoicePaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: Literal["CASH", "BANK_TRANSFER", "POS", "CHEQUE", "OTHER"]
    payment_date: date = Field(default_factory=date.today)
    reference: str = Field(min_length=2, max_length=100)
    receiving_account_id: UUID
    note: str | None = None
