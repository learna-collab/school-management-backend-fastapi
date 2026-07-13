from sqlalchemy import select

from app.models.classes import Class
from app.models.user import User


class RegistrationRepository:
    # =====================================
    # CLASS
    # =====================================

    async def get_class(
        self,
        db,
        class_id,
    ):
        result = await db.execute(
            select(Class).where(
                Class.id == class_id,
            )
        )

        return result.scalar_one_or_none()

    # =====================================
    # USER
    # =====================================

    async def email_exists(
        self,
        db,
        email: str,
    ):
        result = await db.execute(
            select(User).where(
                User.email == email,
            )
        )

        return result.scalar_one_or_none()

    async def username_exists(
        self,
        db,
        username: str,
        school_id,
    ):
        result = await db.execute(
            select(User).where(
                User.username == username,
                User.school_id == school_id,
            )
        )

        return result.scalar_one_or_none()

    async def save(
        self,
        db,
        obj,
    ):
        db.add(obj)

        await db.commit()

        await db.refresh(obj)

        return obj


registration_repo = RegistrationRepository()
