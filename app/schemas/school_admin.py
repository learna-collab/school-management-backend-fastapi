from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr


class UpdateStudentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str
    last_name: str
    email: EmailStr
    gender: str
    date_of_birth: date | None = None
    admission_date: date
    class_name: str


class UpdateTeacherRequest(BaseModel):
    first_name: str
    last_name: str
    email: str


class UpdateClassRequest(BaseModel):
    name: str
    level: str | None = None


class UpdateSubjectRequest(BaseModel):
    name: str
