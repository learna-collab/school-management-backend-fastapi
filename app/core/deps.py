from typing import Annotated

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User, UserRole
from app.utils.helper import JWTBearer

# =====================================================
# JWT AUTH SCHEME
# =====================================================
oauth2_scheme = JWTBearer()


# =====================================================
# GET CURRENT USER (CORE AUTH)
# =====================================================
async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    access_token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            access_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        user_id: str = payload.get("sub")

        if not user_id:
            raise credentials_exception

    except JWTError:
        raise credentials_exception  # noqa: B904

    stmt = select(User).where(User.id == user_id).options(selectinload(User.school))

    result = await session.execute(stmt)

    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Inactive user account",
        )

    return user


# =====================================================
# VERIFIED USER GUARD
# =====================================================
async def requires_verified_user(user: Annotated[User, Depends(get_current_user)]):
    if hasattr(user, "is_verified") and not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Email verification required",
        )
    return user


# =====================================================
# ROLE BASED ACCESS CONTROL (RBAC)
# =====================================================
def require_roles(*allowed_roles: UserRole):
    def dependency(user: Annotated[User, Depends(get_current_user)]):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {allowed_roles}",
            )

        return user

    return dependency


# =====================================================
# ADMIN ONLY
# =====================================================
def require_admin(user: Annotated[User, Depends(get_current_user)]):
    if user.role not in {UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return user


# =====================================================
# SUPER ADMIN ONLY
# =====================================================
def require_superadmin(user: Annotated[User, Depends(get_current_user)]):
    if user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Super admin access required",
        )

    return user


# =====================================================
# SCHOOL ADMIN ONLY
# =====================================================
def require_school_admin(user: Annotated[User, Depends(get_current_user)]):
    if user.role != UserRole.SCHOOL_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="School admin access required",
        )
    return user


def require_teacher(user: Annotated[User, Depends(get_current_user)]):
    if user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=403,
            detail="School admin access required",
        )
    return user


def require_student(user: Annotated[User, Depends(get_current_user)]):
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403,
            detail="School admin access required",
        )
    return user


# =====================================================
# MULTI-SCHOOL ISOLATION GUARD (CRITICAL FOR SAAS)
# =====================================================
def require_same_school_resource(resource_school_id: str):
    def dependency(user: CurrentUser):
        if str(user.school_id) != str(resource_school_id):
            raise HTTPException(
                status_code=403,
                detail="Cross-school access denied",
            )

        return True

    return dependency


async def require_student_or_school_admin(
    user: Annotated[User, Depends(get_current_user)],
):
    if user.role not in (
        UserRole.STUDENT,
        UserRole.SCHOOL_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized.",
        )

    return user


RequireStudentOrSchoolAdmin = Annotated[User, Depends(require_student_or_school_admin)]


# =====================================================
# COMMON TYPE ALIASES (CLEANER ENDPOINTS)
# =====================================================
DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
VerifiedUser = Annotated[User, Depends(requires_verified_user)]
RequireAdmin = Annotated[User, Depends(require_admin)]
RequireSuperAdmin = Annotated[User, Depends(require_superadmin)]
RequireSchoolAdmin = Annotated[User, Depends(require_school_admin)]
RequireTeacher = Annotated[User, Depends(require_teacher)]
RequireStudent = Annotated[User, Depends(require_student)]
