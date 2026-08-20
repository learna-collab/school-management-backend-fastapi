from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DirectorySchoolListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str

    logo_url: str | None = None
    directory_cover_image: str | None = None

    city: str | None = None
    state: str | None = None

    school_type: str | None = None
    ownership_type: str | None = None

    is_directory_verified: bool


class DirectorySchoolDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str

    description: str | None = None

    logo_url: str | None = None
    directory_cover_image: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None

    email: str | None = None
    phone: str | None = None
    whatsapp_number: str | None = None
    website: str | None = None

    school_type: str | None = None
    ownership_type: str | None = None

    founded_year: int | None = None

    average_fee_range: str | None = None
    population_range: str | None = None

    is_directory_verified: bool


class DirectorySchoolListResponse(BaseModel):
    items: list[DirectorySchoolListItem]

    page: int
    page_size: int
    total: int
    total_pages: int


class DirectorySchoolUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    description: str | None = None

    email: str | None = None
    phone: str | None = None
    whatsapp_number: str | None = None
    website: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None

    school_type: str | None = None
    ownership_type: str | None = None

    founded_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
    )

    logo_url: str | None = None
    directory_cover_image: str | None = None

    average_fee_range: str | None = None
    population_range: str | None = None


class DirectoryVisibilityUpdate(BaseModel):
    is_directory_visible: bool


class DirectoryVerificationUpdate(BaseModel):
    is_directory_verified: bool


class DirectoryFeaturedUpdate(BaseModel):
    is_directory_featured: bool
