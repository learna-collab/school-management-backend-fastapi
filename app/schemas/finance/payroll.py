from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

class PayrollCreate(BaseModel):
    employee_user_id: UUID
    pay_year: int = Field(ge=2020, le=2100)
    pay_month: int = Field(ge=1, le=12)
    basic_salary: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    allowances: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    deductions: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    note: str | None = None

class PayrollPayRequest(BaseModel):
    payment_date: date = Field(default_factory=date.today)
    payment_method: Literal["CASH", "BANK_TRANSFER", "POS", "CHEQUE", "OTHER"]
    reference: str = Field(min_length=2, max_length=100)
    payment_account_id: UUID

class SalaryProfileCreate(BaseModel):
    employee_user_id: UUID
    basic_salary: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    default_allowances: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    default_deductions: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    note: str | None = None
