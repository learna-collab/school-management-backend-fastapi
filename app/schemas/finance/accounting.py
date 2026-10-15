from typing import Literal
from pydantic import BaseModel, Field

class FinanceAccountCreate(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=2, max_length=120)
    account_type: Literal["ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"]
    description: str | None = None
