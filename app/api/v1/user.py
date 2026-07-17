from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import RequireSuperAdmin
from app.db.database import get_db
from app.services.user_service import UserService

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

service = UserService()


# =====================================
# GET ALL USERS
# =====================================
@router.get("/")
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: RequireSuperAdmin,
):
    users = await service.get_all_users(db)

    return {
        "users": users,
    }


# =====================================
# GET SINGLE USER
# =====================================
@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: RequireSuperAdmin,
):
    user = await service.get_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return {
        "user": user,
    }


# =====================================
# DELETE USER
# =====================================
@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: RequireSuperAdmin,
):
    deleted = await service.delete_user(db, user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return {
        "message": "User deleted successfully",
    }
