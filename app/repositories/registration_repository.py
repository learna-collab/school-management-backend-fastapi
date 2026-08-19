import re

from sqlalchemy import func, select

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

    async def get_class_by_name(
        self,
        db,
        school_id,
        name: str,
    ):
        """
        Find a class belonging to a school by name.

        Class names are normalized before comparison so values such as:

            JSS1
            JSS 1
            jss1
            jss 1
            JSS-1

        can resolve to the same class.
        """

        if not name:
            return None

        normalized_name = re.sub(
            r"[^a-z0-9]",
            "",
            name.strip().lower(),
        )

        result = await db.execute(
            select(Class).where(
                Class.school_id == school_id,
            )
        )

        classes = result.scalars().all()

        for school_class in classes:
            class_name = re.sub(
                r"[^a-z0-9]",
                "",
                (school_class.name or "").strip().lower(),
            )

            if class_name == normalized_name:
                return school_class

        return None

    async def get_class_names(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(
                Class.name,
            )
            .where(
                Class.school_id == school_id,
            )
            .order_by(
                Class.sort_order,
                Class.name,
            )
        )

        return result.scalars().all()

    async def get_school_classes(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(Class)
            .where(
                Class.school_id == school_id,
            )
            .order_by(
                Class.sort_order,
                Class.name,
            )
        )

        return result.scalars().all()

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
                func.lower(User.email) == email.strip().lower(),
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

    # =====================================
    # SAVE
    # =====================================

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
