from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr

# ===============================
# STUDENT
# ===============================


class StudentRegistrationCreate(BaseModel):
    first_name: str
    last_name: str

    email: EmailStr

    gender: str
    date_of_birth: date
    admission_date: date

    class_name: str


# ===============================
# TEACHER
# ===============================


class TeacherRegistrationCreate(BaseModel):
    first_name: str
    last_name: str

    email: EmailStr

    qualification: str
    specialization: str

    hire_date: date

    class_name: str | None


# ===============================
# PARENT
# ===============================


class BatchImportResponse(BaseModel):
    total: int
    success: int
    failed: int
    users: list[dict]


class ParentRegistrationCreate(BaseModel):
    first_name: str
    last_name: str

    email: EmailStr

    occupation: str
    phone: str


# ===============================
# RESPONSE
# ===============================


class RegistrationResponse(BaseModel):
    username: str
    password: str

    first_name: str
    last_name: str

    role: Literal[
        "STUDENT",
        "TEACHER",
        "PARENT",
    ]
