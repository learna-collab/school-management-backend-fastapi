from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_sheet import AttendanceSheet
from app.models.class_subject import ClassSubject
from app.models.class_teacher import ClassTeacher
from app.models.classes import Class
from app.models.enrollment import StudentEnrollment
from app.models.subject import Subject
from app.models.teacher_class_subject import TeacherClassSubject


class SchoolClassRepository:
    # ==========================================================
    # CLASS DASHBOARD
    # ==========================================================

    async def get_class_dashboard(
        self,
        db: AsyncSession,
        class_id: UUID,
        session_id: UUID,
    ):
        cls = await db.get(
            Class,
            class_id,
        )

        if not cls:
            return None

        # Students in class
        students_count = await db.scalar(
            select(func.count())
            .select_from(StudentEnrollment)
            .where(
                StudentEnrollment.class_id == class_id,
                StudentEnrollment.session_id == session_id,
            )
        )

        # Class teachers (assigned during signup or later)
        teachers_count = await db.scalar(
            select(func.count())
            .select_from(ClassTeacher)
            .where(
                ClassTeacher.class_id == class_id,
            )
        )

        # Subjects assigned to class
        subjects_count = await db.scalar(
            select(func.count())
            .select_from(ClassSubject)
            .where(
                ClassSubject.class_id == class_id,
            )
        )

        return {
            "id": str(cls.id),
            "name": cls.name,
            "level": cls.level,
            "students_count": students_count or 0,
            "teachers_count": teachers_count or 0,
            "subjects_count": subjects_count or 0,
        }

    # ==========================================================
    # CREATE
    # ==========================================================

    async def create(
        self,
        db: AsyncSession,
        cls: Class,
    ):
        db.add(cls)

        await db.commit()

        await db.refresh(cls)

        return cls

    # ==========================================================
    # GET BY SCHOOL
    # ==========================================================

    async def get_by_school(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        result = await db.execute(
            select(
                Class,
                func.count(distinct(StudentEnrollment.student_id)).label(
                    "students_count"
                ),
                func.count(distinct(ClassTeacher.teacher_id)).label("teachers_count"),
                func.count(distinct(ClassSubject.subject_id)).label("subjects_count"),
            )
            .outerjoin(
                StudentEnrollment,
                StudentEnrollment.class_id == Class.id,
            )
            .outerjoin(
                ClassTeacher,
                ClassTeacher.class_id == Class.id,
            )
            .outerjoin(
                ClassSubject,
                ClassSubject.class_id == Class.id,
            )
            .where(
                Class.school_id == school_id,
            )
            .group_by(Class.id)
            .order_by(
                Class.created_at.desc(),
            )
        )

        return [
            {
                "id": str(cls.id),
                "name": cls.name,
                "level": cls.level,
                "students_count": students_count,
                "teachers_count": teachers_count,
                "subjects_count": subjects_count,
            }
            for cls, students_count, teachers_count, subjects_count in result.all()
        ]

    # ==========================================================
    # GET SINGLE
    # ==========================================================

    async def get_by_id(
        self,
        db: AsyncSession,
        class_id: UUID,
    ):
        return await db.get(
            Class,
            class_id,
        )

    # ==========================================================
    # DELETE
    # ==========================================================

    async def delete(
        self,
        db: AsyncSession,
        class_id: UUID,
    ):
        cls = await db.get(
            Class,
            class_id,
        )
        attendance_exists = await db.scalar(
            select(AttendanceSheet.id).where(AttendanceSheet.class_id == class_id)
        )
        if attendance_exists:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this class because attendance records already exist.",
            )

        if not cls:
            return False

        await db.delete(cls)

        await db.commit()

        return True

    async def get_class_basic_info(
        self,
        db: AsyncSession,
        class_id: UUID,
    ):
        cls = await db.get(
            Class,
            class_id,
        )

        if not cls:
            return None

        return {
            "id": str(cls.id),
            "name": cls.name,
            "level": cls.level,
        }


school_class_repository = SchoolClassRepository()
