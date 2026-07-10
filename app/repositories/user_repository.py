from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.school import School
from app.models.user import User, UserRole


class UserRepository:
    # =====================================================
    # CREATE USER
    # =====================================================

    async def create(
        self,
        db: AsyncSession,
        user: User,
    ):
        db.add(user)

        await db.commit()

        await db.refresh(user)

        result = await db.execute(
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.school),
                selectinload(User.credential),
            )
        )

        return result.scalar_one()

    # =====================================================
    # SAVE USER
    # =====================================================

    async def save(
        self,
        db: AsyncSession,
        user: User,
    ):
        db.add(user)

        await db.commit()

        await db.refresh(user)

        result = await db.execute(
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.school),
                selectinload(User.credential),
            )
        )

        return result.scalar_one()

    # =====================================================
    # GET BY EMAIL
    # =====================================================

    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
    ):
        result = await db.execute(
            select(User)
            .where(User.email == email)
            .options(
                selectinload(User.school),
                selectinload(User.credential),
            )
        )

        return result.scalar_one_or_none()

    # =====================================================
    # SAVE ACCESS TOKEN
    # =====================================================

    async def save_access_token(
        self,
        db: AsyncSession,
        user: User,
        access_token: str,
    ):
        user.access_token = access_token

        return await self.save(
            db,
            user,
        )

    # =====================================================
    # GET BY ID
    # =====================================================

    async def get_by_id(
        self,
        db: AsyncSession,
        user_id: str,
    ):
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.school),
                selectinload(User.credential),
            )
        )

        return result.scalar_one_or_none()

    # =====================================================
    # GET BY USERNAME
    # =====================================================

    async def get_by_username(
        self,
        db: AsyncSession,
        username: str,
    ):
        result = await db.execute(
            select(User)
            .where(User.username == username)
            .options(
                selectinload(User.school),
                selectinload(User.credential),
            )
        )

        return result.scalar_one_or_none()

    # =====================================================
    # GET SCHOOL BY SLUG
    # =====================================================

    async def get_school_by_slug(
        self,
        db: AsyncSession,
        slug: str,
    ):
        result = await db.execute(select(School).where(School.slug == slug))

        return result.scalar_one_or_none()

    # =====================================================
    # GET USER BY USERNAME & SCHOOL
    # =====================================================

    async def get_user_by_username_and_school(
        self,
        db: AsyncSession,
        username: str,
        school_id: str,
    ):
        result = await db.execute(
            select(User)
            .where(
                User.username == username,
                User.school_id == school_id,
            )
            .options(
                selectinload(User.school),
                selectinload(User.credential),
            )
        )

        return result.scalar_one_or_none()

    # =====================================================
    # GET ALL USERS
    # =====================================================

    async def get_all(
        self,
        db: AsyncSession,
    ):
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.school),
                selectinload(User.credential),
            )
            .order_by(User.created_at.desc())
        )

        return result.scalars().all()

    # =====================================================
    # GET STUDENTS
    # =====================================================

    async def get_students(
        self,
        db: AsyncSession,
        school_id,
    ):
        result = await db.execute(
            select(User)
            .where(
                User.school_id == school_id,
                User.role == UserRole.STUDENT,
            )
            .options(
                selectinload(User.student_profile),
                selectinload(User.credential),
            )
            .order_by(
                User.first_name,
                User.last_name,
            )
        )

        return result.scalars().all()

    # =====================================================
    # GET TEACHERS
    # =====================================================

    async def get_teachers(
        self,
        db: AsyncSession,
        school_id,
    ):
        result = await db.execute(
            select(User)
            .where(
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
            )
            .options(
                selectinload(User.teacher_profile),
                selectinload(User.credential),
            )
            .order_by(
                User.first_name,
                User.last_name,
            )
        )

        return result.scalars().all()

    # =====================================================
    # GET PARENTS
    # =====================================================

    async def get_parents(
        self,
        db: AsyncSession,
        school_id,
    ):
        result = await db.execute(
            select(User)
            .where(
                User.school_id == school_id,
                User.role == UserRole.PARENT,
            )
            .options(
                selectinload(User.parent_profile),
                selectinload(User.credential),
            )
            .order_by(
                User.first_name,
                User.last_name,
            )
        )

        return result.scalars().all()

    # =====================================================
    # DELETE USER
    # =====================================================

    async def delete(
        self,
        db: AsyncSession,
        user: User,
    ):
        await db.delete(user)

        await db.commit()

    # =====================================================
    # LOGIN
    # =====================================================

    async def get_by_school_slug_and_username(
        self,
        db: AsyncSession,
        school_slug: str,
        username: str,
    ):
        result = await db.execute(
            select(User)
            .join(
                School,
                User.school_id == School.id,
            )
            .where(
                School.slug == school_slug,
                User.username == username,
            )
            .options(
                selectinload(User.school),
                selectinload(User.credential),
            )
        )

        return result.scalar_one_or_none()


user_repo = UserRepository()
