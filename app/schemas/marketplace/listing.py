from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.marketplace.listing import (
    ListingStatus,
    ListingType,
)


class ListingCreate(BaseModel):
    category_id: UUID

    listing_type: ListingType

    title: str = Field(
        min_length=2,
        max_length=255,
    )

    description: str | None = None

    price: Decimal = Field(gt=0)

    currency: str = Field(
        default="NGN",
        min_length=3,
        max_length=3,
    )


class ListingUpdate(BaseModel):
    category_id: UUID | None = None

    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    description: str | None = None

    price: Decimal | None = Field(
        default=None,
        gt=0,
    )

    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )

    status: ListingStatus | None = None


class PhysicalProductCreate(BaseModel):
    sku: str | None = Field(
        default=None,
        max_length=100,
    )

    stock_quantity: int = Field(
        default=0,
        ge=0,
    )

    weight_kg: Decimal | None = Field(
        default=None,
        ge=0,
    )

    dimensions: str | None = None


class PhysicalProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str | None

    stock_quantity: int

    weight_kg: Decimal | None

    dimensions: str | None


class ServiceCreate(BaseModel):
    pricing_model: str = "FIXED"

    duration_minutes: int | None = Field(
        default=None,
        ge=1,
    )

    service_area: str | None = None

    availability: str | None = None


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pricing_model: str

    duration_minutes: int | None

    service_area: str | None

    availability: str | None


class DigitalProductCreate(BaseModel):
    file_url: str | None = None

    file_type: str | None = None

    access_type: str = "DOWNLOAD"

    instructions: str | None = None


class DigitalProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_url: str | None

    file_type: str | None

    access_type: str

    instructions: str | None


class ListingImageCreate(BaseModel):
    image_url: str

    is_primary: bool = False

    sort_order: int = 0


class ListingImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    image_url: str

    is_primary: bool

    sort_order: int


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    vendor_id: UUID

    category_id: UUID

    listing_type: ListingType

    title: str

    slug: str

    description: str | None

    price: Decimal

    currency: str

    status: ListingStatus

    is_featured: bool

    images: list[ListingImageResponse] = []

    physical: PhysicalProductResponse | None = None

    service: ServiceResponse | None = None

    digital: DigitalProductResponse | None = None
