from datetime import date
from uuid import UUID

from pydantic import BaseModel

# =========================
# Sessions
# =========================


class SessionCreate(BaseModel):
    name: str
    start_date: date
    end_date: date


class SessionUpdate(BaseModel):
    name: str
    start_date: date
    end_date: date


class SessionResponse(BaseModel):
    id: UUID
    name: str
    start_date: date
    end_date: date
    is_active: bool

    class Config:
        from_attributes = True


# =========================
# Terms
# =========================


class TermCreate(BaseModel):
    name: str
    sort_order: int = 1


class TermUpdate(BaseModel):
    name: str
    sort_order: int


class TermResponse(BaseModel):
    id: UUID
    name: str
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True
