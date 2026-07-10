from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    role: str
    school_id: UUID | None
    first_name: str | None
    last_name: str | None


class UserOut(UserBase):
    id: UUID
    profile_completed: bool
    school_id: UUID | None = None
    school_name: str | None = None
    school_logo: str | None = None
    model_config = ConfigDict(from_attributes=True)


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    school_id: UUID | None = None
    profile_completed: bool
    is_active: bool
    model_config = ConfigDict(from_attributes=True)
