from sqlalchemy import func, select

from app.models.academic_session import AcademicSession
from app.models.attendance_record import AttendanceRecord
from app.models.classes import Class
from app.models.result_batch import ResultBatch
from app.models.school import School
from app.models.subject import Subject
from app.models.terms import Term
from app.models.user import User, UserRole


class SchoolAdminDashboardRepository:
    # =====================================================
    # USERS
    # =====================================================

    async def count_students(self, db, school_id):
        result = await db.execute(
            select(func.count(User.id)).where(
                User.school_id == school_id,
                User.role == UserRole.STUDENT,
            )
        )

        return result.scalar() or 0

    async def get_school(
        self,
        db,
        school_id,
    ):
        result = await db.execute(select(School).where(School.id == school_id))

        return result.scalar_one_or_none()

    async def count_teachers(self, db, school_id):
        result = await db.execute(
            select(func.count(User.id)).where(
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
            )
        )

        return result.scalar() or 0

    async def count_parents(self, db, school_id):
        result = await db.execute(
            select(func.count(User.id)).where(
                User.school_id == school_id,
                User.role == UserRole.PARENT,
            )
        )

        return result.scalar() or 0

    # =====================================================
    # ACADEMICS
    # =====================================================

    async def count_classes(self, db, school_id):
        result = await db.execute(
            select(func.count(Class.id)).where(
                Class.school_id == school_id,
            )
        )

        return result.scalar() or 0

    async def count_subjects(self, db, school_id):
        result = await db.execute(
            select(func.count(Subject.id)).where(
                Subject.school_id == school_id,
            )
        )

        return result.scalar() or 0

    async def get_active_session(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(AcademicSession)
            .where(
                AcademicSession.school_id == school_id,
                AcademicSession.is_active.is_(True),
            )
            .limit(1)
        )

        return result.scalars().first()

    async def get_active_term(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(Term)
            .where(
                Term.school_id == school_id,
                Term.is_active.is_(True),
            )
            .limit(1)
        )

        return result.scalars().first()

    # =====================================================
    # ATTENDANCE
    # =====================================================

    async def attendance_summary(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(
                AttendanceRecord.status,
                func.count(AttendanceRecord.id),
            )
            .where(
                AttendanceRecord.school_id == school_id,
            )
            .group_by(AttendanceRecord.status)
        )

        rows = result.all()

        summary = {
            "present": 0,
            "absent": 0,
            "late": 0,
        }

        for status, count in rows:
            summary[status.value.lower()] = count

        return summary

    # =====================================================
    # RESULTS
    # =====================================================

    async def count_result_batches(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(func.count(ResultBatch.id)).where(
                ResultBatch.school_id == school_id,
            )
        )

        return result.scalar() or 0

    async def count_approved_batches(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(func.count(ResultBatch.id)).where(
                ResultBatch.school_id == school_id,
                ResultBatch.status == "APPROVED",
            )
        )

        return result.scalar() or 0

    async def count_pending_batches(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(func.count(ResultBatch.id)).where(
                ResultBatch.school_id == school_id,
                ResultBatch.status.in_(
                    [
                        "DRAFT",
                        "SUBMITTED",
                        "REJECTED",
                    ]
                ),
            )
        )

        return result.scalar() or 0

    async def count_published_batches(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(func.count(ResultBatch.id)).where(
                ResultBatch.school_id == school_id,
                ResultBatch.status == "PUBLISHED",
            )
        )

        return result.scalar() or 0

    # =====================================================
    # RECENT USERS
    # =====================================================

    async def latest_students(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(User)
            .where(
                User.school_id == school_id,
                User.role == UserRole.STUDENT,
            )
            .order_by(User.created_at.desc())
            .limit(5)
        )

        return result.scalars().all()

    async def latest_teachers(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(User)
            .where(
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
            )
            .order_by(User.created_at.desc())
            .limit(5)
        )

        return result.scalars().all()
