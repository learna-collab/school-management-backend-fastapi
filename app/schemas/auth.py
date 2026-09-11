from pydantic import BaseModel, EmailStr

from app.schemas.user import UserPublic


class VendorLoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class RegisterResponse(BaseModel):
    message: str
    user: UserPublic
