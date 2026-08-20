from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SchoolFacilityBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    is_available: bool = True


class SchoolFacilityCreate(SchoolFacilityBase):
    pass


class SchoolFacilityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_available: bool | None = None


class SchoolFacilityResponse(SchoolFacilityBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    school_id: UUID
