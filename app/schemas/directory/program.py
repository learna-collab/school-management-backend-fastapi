from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DIRECTORY_PROGRAM_OPTIONS = [
    "Nursery",
    "Primary",
    "Junior Secondary",
    "Senior Secondary",
    "Boarding School",
    "Day School",
    "WAEC",
    "NECO",
    "Cambridge",
    "Montessori",
    "Technical/Vocational",
]


class SchoolProgramCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=150,
    )

    description: str | None = None

    is_available: bool = True


class SchoolProgramUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    description: str | None = None

    is_available: bool | None = None


class SchoolProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    school_id: UUID

    name: str
    description: str | None

    is_available: bool
