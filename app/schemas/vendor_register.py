from pydantic import BaseModel, EmailStr, Field


class VendorRegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)


class VendorRegisterResponse(BaseModel):
    message: str
    email: EmailStr
