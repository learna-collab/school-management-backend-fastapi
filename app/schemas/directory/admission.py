from datetime import date
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.school_admission import AdmissionCategory


class SchoolAdmissionCreate(BaseModel):
    session_name: str = Field(
        min_length=4,
        max_length=100,
    )

    title: str = Field(
        min_length=3,
        max_length=255,
    )

    category: AdmissionCategory

    description: str | None = None

    requirements: str | None = None

    application_fee: str | None = Field(
        default=None,
        max_length=100,
    )

    application_deadline: date | None = None

    application_url: AnyHttpUrl | None = None

    is_open: bool = True

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return value.strip()


class SchoolAdmissionUpdate(BaseModel):
    session_name: str | None = Field(
        default=None,
        min_length=4,
        max_length=100,
    )

    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
    )

    category: AdmissionCategory | None = None

    description: str | None = None

    requirements: str | None = None

    application_fee: str | None = Field(
        default=None,
        max_length=100,
    )

    application_deadline: date | None = None

    application_url: AnyHttpUrl | None = None

    is_open: bool | None = None

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip()

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip()


class SchoolAdmissionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    school_id: UUID

    session_name: str
    title: str
    category: AdmissionCategory

    description: str | None
    requirements: str | None

    application_fee: str | None

    application_deadline: date | None

    brochure_url: str | None

    application_url: str | None

    is_open: bool


class AdmissionStatusUpdate(BaseModel):
    is_open: bool


class PublicAdmissionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    session_name: str
    title: str
    category: AdmissionCategory

    description: str | None
    requirements: str | None

    application_fee: str | None

    application_deadline: date | None

    brochure_url: str | None
    application_url: str | None

    is_open: bool
