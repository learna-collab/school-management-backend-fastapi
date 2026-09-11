from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=150,
    )

    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    description: str | None = None

    is_active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    name: str
    slug: str

    description: str | None

    is_active: bool
