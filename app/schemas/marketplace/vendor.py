from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.marketplace.vendor import (
    VendorStatus,
    VendorType,
)


class VendorCreate(BaseModel):
    vendor_type: VendorType

    store_name: str = Field(
        min_length=2,
        max_length=255,
    )

    business_name: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None

    phone: str | None = Field(
        default=None,
        max_length=50,
    )

    public_email: EmailStr | None = None

    address: str | None = None

    logo_url: str | None = None


class VendorUpdate(BaseModel):
    store_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    business_name: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None

    phone: str | None = Field(
        default=None,
        max_length=50,
    )

    public_email: EmailStr | None = None

    address: str | None = None

    logo_url: str | None = None


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID

    vendor_type: VendorType

    business_name: str | None
    store_name: str
    slug: str

    description: str | None
    phone: str | None
    public_email: EmailStr | None
    address: str | None
    logo_url: str | None

    status: VendorStatus
    is_active: bool


class VendorPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    vendor_type: VendorType

    business_name: str | None
    store_name: str
    slug: str

    description: str | None

    phone: str | None

    public_email: EmailStr | None

    address: str | None

    logo_url: str | None


class VendorStatusUpdate(BaseModel):
    status: VendorStatus
