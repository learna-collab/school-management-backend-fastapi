from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

class ExpenseCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)

class ExpenseCreate(BaseModel):
    category_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: Literal["CASH", "BANK_TRANSFER", "POS", "CHEQUE", "OTHER"]
    expense_date: date = Field(default_factory=date.today)
    description: str = Field(min_length=3)
    reference: str | None = Field(default=None, max_length=100)
    payment_account_id: UUID
    expense_account_id: UUID | None = None
