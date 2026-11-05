from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.classes import Class
from app.models.subject import Subject
from app.models.user import User, UserRole


class SchoolAdminRepository:
    # =========================
    # STATS (USERS BASED)
    # =========================
    async def count_students(self, db: AsyncSession, school_id: str):
        result = await db.execute(
            select(func.count(User.id)).where(
                User.school_id == school_id,
                User.role == UserRole.STUDENT,
            ),
        )
        return result.scalar() or 0

    async def count_teachers(self, db: AsyncSession, school_id: str):
        result = await db.execute(
            select(func.count(User.id)).where(
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
            ),
        )
        return result.scalar() or 0

    async def count_classes(self, db: AsyncSession, school_id: str):
        result = await db.execute(
            select(func.count(Class.id)).where(Class.school_id == school_id),
        )
        return result.scalar() or 0

    # =========================
    # LIST STUDENTS (WITH PROFILE JOIN)
    # =========================
    async def get_students(self, db: AsyncSession, school_id: str):
        result = await db.execute(
            select(User).where(
                User.school_id == school_id,
                User.role == UserRole.STUDENT,
            ),
        )
        return result.scalars().all()

    # =========================
    # LIST TEACHERS
    # =========================
    async def get_teachers(self, db: AsyncSession, school_id: str):
        result = await db.execute(
            select(User).where(
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
            ),
        )
        return result.scalars().all()

    # ==================================================
    # UPDATE STUDENT
    # ==================================================

    async def get_student_by_id(
        self,
        db: AsyncSession,
        school_id: UUID,
        student_id: UUID,
    ):
        result = await db.execute(
            select(User)
            .where(
                User.id == student_id,
                User.school_id == school_id,
                User.role == UserRole.STUDENT,
            )
            .options(
                selectinload(User.student_profile),
            )
        )

        return result.scalar_one_or_none()

    # ==================================================
    # UPDATE TEACHER
    # ==================================================

    async def get_teacher_by_id(
        self,
        db: AsyncSession,
        school_id: UUID,
        teacher_id: UUID,
    ):
        result = await db.execute(
            select(User).where(
                User.id == teacher_id,
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
            )
        )
        return result.scalar_one_or_none()

    # ==================================================
    # UPDATE CLASS
    # ==================================================

    async def get_class_by_id(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
    ):
        result = await db.execute(
            select(Class).where(
                Class.id == class_id,
                Class.school_id == school_id,
            )
        )
        return result.scalar_one_or_none()

    # ==================================================
    # SUBJECTS
    # ==================================================

    async def get_subject_by_id(
        self,
        db: AsyncSession,
        school_id: UUID,
        subject_id: UUID,
    ):
        result = await db.execute(
            select(Subject).where(
                Subject.id == subject_id,
                Subject.school_id == school_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_subject(
        self,
        db: AsyncSession,
        subject: Subject,
    ):
        await db.delete(subject)

    # ==================================================
    # SAVE
    # ==================================================

    async def commit(self, db: AsyncSession):
        await db.commit()

    async def refresh(self, db: AsyncSession, obj):
        await db.refresh(obj)

    async def get_class_by_name(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_name: str,
    ):
        result = await db.execute(
            select(Class).where(
                Class.school_id == school_id,
                func.lower(Class.name) == class_name.strip().lower(),
            )
        )

        return result.scalar_one_or_none()


school_admin_repo = SchoolAdminRepository()
