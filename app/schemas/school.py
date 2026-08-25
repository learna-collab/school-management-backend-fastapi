from typing import Optional

from pydantic import BaseModel, EmailStr


class SchoolUpdate(BaseModel):
    # ==========================
    # SCHOOL
    # ==========================
    school_name: str
    website: str | None = None
    phone: str
    whatsapp_number: str | None = None
    state: str
    address: str
    description: str | None = None

    # ==========================
    # SCHOOL ADMIN
    # ==========================
    admin_first_name: str
    admin_last_name: str
    admin_email: str


class SchoolCreate(BaseModel):
    # School
    school_name: str
    website: str | None = None
    phone: str
    whatsapp_number: str | None = None
    state: str
    address: str
    description: str | None = None

    # School Admin
    admin_first_name: str
    admin_last_name: str
    admin_email: EmailStr


class SchoolOnboardingRequest(BaseModel):
    # School

    school_name: str
    website: str | None = None

    address: str
    state: str

    phone: str
    whatsapp_number: str | None = None

    description: str | None = None

    average_fee_range: str | None = None
    population_range: str | None = None

    referral_source: str | None = None

    # Admin

    admin_first_name: str
    admin_last_name: str

    admin_email: EmailStr
    admin_password: str
