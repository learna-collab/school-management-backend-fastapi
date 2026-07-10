from sqlalchemy import func, select

from app.models.school import School
from app.models.user import User, UserRole


class AdminRepository:
    async def count_schools(self, db):
        result = await db.execute(select(func.count(School.id)))

        return result.scalar() or 0

    async def count_users(self, db):
        result = await db.execute(select(func.count(User.id)))

        return result.scalar() or 0

    async def count_school_admins(self, db):
        result = await db.execute(
            select(func.count(User.id)).where(User.role == UserRole.SCHOOL_ADMIN)
        )

        return result.scalar() or 0

    # =====================================
    # USERS
    # =====================================

    # CREATE USER
    async def create_user(self, db, user):
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    # GET USER
    async def get_user(self, db, user_id):
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    # DELETE USER
    async def delete_user(self, db, user):
        await db.delete(user)
        await db.commit()
        return True

    async def get_admins(self, db):
        result = await db.execute(
            select(User).where(
                User.role.in_(
                    [
                        UserRole.SCHOOL_ADMIN,
                        UserRole.SUPER_ADMIN,
                    ],
                ),
            ),
        )

        admins = result.scalars().all()

        return [
            {
                "id": admin.id,
                "email": admin.email,
                "role": admin.role,
                "school_id": admin.school_id,
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "created_at": getattr(admin, "created_at", None),
            }
            for admin in admins
        ]

    # SAVE USER
    async def save_user(self, db, user):
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def save(
        self,
        db,
        obj,
    ):
        db.add(obj)

        await db.commit()

        await db.refresh(obj)

        return obj
