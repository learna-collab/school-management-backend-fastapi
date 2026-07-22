from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser
from app.db.database import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
)
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])

auth_service = AuthService()


# =====================================================
# REGISTER USER (INVITE-BASED ONLY)
# =====================================================
@router.post(
    "/register",
)
@router.post("/register")
async def register(
    response: Response,
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await auth_service.register(
        db=db,
        email=payload.email,
        password=payload.password,
        username=payload.username,
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired invite code",
        )

    # 🔐 AUTO LOGIN AFTER REGISTER
    result = await auth_service.login(
        db,
        payload.username,
        payload.password,
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Account created but login failed",
        )

    # 🍪 set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=60 * 60 * 24 * 30,
    )

    return {
        "access_token": result["access_token"],
        "user": result["user"],
    }


# =====================================================
# LOGIN
# =====================================================
@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    print(await request.body())
    result = await auth_service.login(
        db,
        payload.username,
        payload.password,
    )

    if not result:
        raise HTTPException(
            status_code=400,
            detail="Invalid credentials",
        )

    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=60 * 60 * 24 * 30,
    )

    return {
        "access_token": result["access_token"],
        "user": result["user"],
    }


@router.post("/refresh")
async def refresh(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    refresh_token: str | None = Cookie(default=None),
):
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Missing refresh token",
        )

    access_token = await auth_service.refresh_access_token(
        db,
        refresh_token,
    )

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    return {"access_token": access_token}


@router.post("/logout")
async def logout(
    response: Response,
):
    response.delete_cookie(
        key="refresh_token",
        secure=True,
        httponly=True,
        samesite="none",
    )

    return {"message": "Logged out"}


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await auth_service.forgot_password(db, payload.email)

    return {"message": "If account exists, reset link sent"}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    success = await auth_service.reset_password(
        db,
        payload.token,
        payload.password,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired token",
        )

    return {"message": "Password updated successfully"}


@router.get("/me", response_model=UserOut)
async def get_current_user(current_user: CurrentUser):
    return current_user
