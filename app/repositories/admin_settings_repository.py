from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.school import School
from app.models.user import User
from app.models.user_credentials import UserCredential


class AdminSettingsRepository:
    """
    Repository responsible for all School Admin settings operations.

    Handles:
        - School profile
        - Password
        - Logo
    """

    # =====================================================
    # SCHOOL
    # =====================================================

    @staticmethod
    async def get_school(
        db: AsyncSession,
        school_id: UUID,
    ) -> School | None:
        result = await db.execute(select(School).where(School.id == school_id))

        return result.scalar_one_or_none()

    @staticmethod
    async def update_school(
        db: AsyncSession,
        school: School,
        **fields,
    ) -> School:
        """Updates only provided fields."""
        for key, value in fields.items():
            setattr(school, key, value)

        await db.commit()
        await db.refresh(school)

        return school

    @staticmethod
    async def update_logo(
        db: AsyncSession,
        school: School,
        logo_url: str,
    ) -> School:
        school.logo_url = logo_url

        await db.commit()
        await db.refresh(school)

        return school

    # =====================================================
    # USER
    # =====================================================

    @staticmethod
    async def get_user(
        db: AsyncSession,
        user_id: UUID,
    ) -> User | None:
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.credential),
                selectinload(User.school),
            )
            .where(User.id == user_id)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def update_user_password(
        db: AsyncSession,
        user: User,
        password_hash: str,
    ) -> User:
        """
        Updates both the users table password_hash.

        and the user_credentials table password.
        """
        user.password_hash = password_hash

        if user.credential:
            user.credential.password = password_hash

        await db.commit()
        await db.refresh(user)

        return user

    # =====================================================
    # CREDENTIALS
    # =====================================================

    @staticmethod
    async def get_user_credentials(
        db: AsyncSession,
        user_id: UUID,
    ) -> UserCredential | None:
        result = await db.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        )

        return result.scalar_one_or_none()
