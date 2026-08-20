from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.admission_enquiry import (
    AdmissionEnquiryStatus,
)


class AdmissionEnquiryCreate(BaseModel):
    parent_name: str = Field(
        min_length=2,
        max_length=255,
    )

    email: str | None = Field(
        default=None,
        max_length=255,
    )

    phone: str = Field(
        min_length=7,
        max_length=50,
    )

    student_name: str | None = Field(
        default=None,
        max_length=255,
    )

    student_class: str | None = Field(
        default=None,
        max_length=100,
    )

    message: str | None = Field(
        default=None,
        max_length=3000,
    )


class AdmissionEnquiryStatusUpdate(BaseModel):
    status: AdmissionEnquiryStatus


class AdmissionEnquiryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    school_id: UUID
    admission_id: UUID

    parent_name: str
    email: str | None
    phone: str

    student_name: str | None
    student_class: str | None
    message: str | None

    status: AdmissionEnquiryStatus

    created_at: datetime
    updated_at: datetime


class AdmissionEnquiryAdminResponse(
    AdmissionEnquiryResponse,
):
    admission_title: str | None = None
    session_name: str | None = None
