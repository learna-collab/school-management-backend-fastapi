from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# =====================================================
# SCHOOL SETTINGS
# =====================================================


class SchoolSettingsResponse(BaseModel):
    id: UUID

    name: str
    email: EmailStr
    phone: str

    address: str | None = None
    state: str | None = None
    website: str | None = None

    description: str | None = None

    contact_person: str | None = None
    whatsapp_number: str | None = None

    logo_url: str | None = None

    subscription_plan: str
    code: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UpdateSchoolSettingsRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)

    email: EmailStr

    phone: str = Field(..., min_length=7, max_length=50)

    address: str | None = Field(default=None, max_length=1000)

    state: str | None = Field(default=None, max_length=100)

    website: str | None = Field(default=None, max_length=255)

    description: str | None = Field(default=None, max_length=2000)

    contact_person: str | None = Field(default=None, max_length=255)

    whatsapp_number: str | None = Field(default=None, max_length=50)


# =====================================================
# PASSWORD
# =====================================================


class ChangePasswordRequest(BaseModel):
    current_password: str

    new_password: str


# =====================================================
# LOGO
# =====================================================


class LogoUploadResponse(BaseModel):
    logo_url: str


# =====================================================
# GENERIC RESPONSE
# =====================================================


class MessageResponse(BaseModel):
    message: str
