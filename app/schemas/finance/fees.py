from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

class FeeCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None

class StudentFeeCreate(BaseModel):
    student_id: UUID
    fee_category_id: UUID
    session_id: UUID
    term_id: UUID
    amount_due: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    note: str | None = Field(default=None, max_length=255)


class BulkStudentFeeCreate(BaseModel):
    fee_category_id: UUID
    session_id: UUID
    term_id: UUID
    amount_due: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    scope: str = Field(pattern="^(ALL_STUDENTS|CLASS)$")
    class_id: UUID | None = None
    note: str | None = Field(default=None, max_length=255)
