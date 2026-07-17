from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.academic_session import AcademicSession
from app.models.attendance_record import (
    AttendanceRecord,
    AttendanceStatus,
)
from app.models.attendance_sheet import AttendanceSheet
from app.models.class_subject import ClassSubject
from app.models.class_teacher import ClassTeacher
from app.models.classes import Class
from app.models.enrollment import StudentEnrollment
from app.models.lesson import Lesson
from app.models.result_batch import ResultBatch
from app.models.result_summary import ResultSummary
from app.models.student import StudentProfile
from app.models.teacher import TeacherProfile
from app.models.teacher_class_subject import TeacherClassSubject
from app.models.terms import Term


class DashboardRepository:
    # ==================================================
    # ACTIVE SESSION
    # ==================================================

    async def get_active_session(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(AcademicSession).where(
                AcademicSession.school_id == school_id,
                AcademicSession.is_active.is_(True),
            )
        )

        return result.scalar_one_or_none()

    async def get_active_term(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(Term).where(
                Term.school_id == school_id,
                Term.is_active.is_(True),
            )
        )

        return result.scalar_one_or_none()

    # ==================================================
    # STUDENT
    # ==================================================

    async def get_student_profile(
        self,
        db,
        user_id,
    ):
        result = await db.execute(
            select(StudentProfile)
            .options(selectinload(StudentProfile.user))
            .where(StudentProfile.user_id == user_id),
        )

        return result.scalar_one_or_none()

    async def get_student_attendance_stats(
        self,
        db,
        student_id,
    ):
        present = await db.scalar(
            select(func.count())
            .select_from(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == AttendanceStatus.PRESENT,
            )
        )

        absent = await db.scalar(
            select(func.count())
            .select_from(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == AttendanceStatus.ABSENT,
            )
        )

        late = await db.scalar(
            select(func.count())
            .select_from(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == AttendanceStatus.LATE,
            )
        )

        return {
            "present": present or 0,
            "absent": absent or 0,
            "late": late or 0,
        }

    async def get_current_student_enrollment(
        self,
        db,
        student_id,
    ):
        result = await db.execute(
            select(StudentEnrollment)
            .options(
                selectinload(StudentEnrollment.school_class),
                selectinload(StudentEnrollment.session),
            )
            .where(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.is_current.is_(True),
            ),
        )

        return result.scalar_one_or_none()

    async def get_student_latest_summary(
        self,
        db,
        student_id,
    ):
        result = await db.execute(
            select(ResultSummary)
            .where(ResultSummary.student_id == student_id)
            .order_by(ResultSummary.created_at.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_recent_lessons(
        self,
        db,
        class_id,
    ):
        result = await db.execute(
            select(Lesson)
            .where(
                Lesson.class_id == class_id,
                Lesson.is_published.is_(True),
            )
            .order_by(Lesson.created_at.desc())
            .limit(5)
        )

        return result.scalars().all()

    # ==================================================
    # TEACHER
    # ==================================================

    async def get_teacher_profile(
        self,
        db,
        user_id,
    ):
        result = await db.execute(
            select(TeacherProfile).where(TeacherProfile.user_id == user_id)
        )

        return result.scalar_one_or_none()

    async def get_class_assignments(
        self,
        db,
        class_id,
    ):
        result = await db.execute(
            select(ClassSubject)
            .options(
                selectinload(ClassSubject.school_class),
                selectinload(ClassSubject.subject),
            )
            .where(ClassSubject.class_id == class_id)
            .order_by(ClassSubject.subject_id)
        )

        return result.scalars().all()

    async def get_teacher_subject_assignments(
        self,
        db,
        teacher_id,
    ):
        result = await db.execute(
            select(TeacherClassSubject)
            .options(
                selectinload(TeacherClassSubject.school_class),
                selectinload(TeacherClassSubject.subject),
            )
            .where(
                TeacherClassSubject.teacher_id == teacher_id,
            )
            .order_by(
                TeacherClassSubject.class_id,
                TeacherClassSubject.subject_id,
            )
        )

        return result.scalars().all()

    async def count_teacher_lessons(
        self,
        db,
        teacher_id,
    ):
        return await db.scalar(
            select(func.count())
            .select_from(Lesson)
            .where(Lesson.created_by == teacher_id)
        )

    async def count_teacher_attendance(
        self,
        db,
        teacher_id,
    ):
        return await db.scalar(
            select(func.count())
            .select_from(AttendanceSheet)
            .where(AttendanceSheet.marked_by == teacher_id)
        )

    async def count_teacher_results(
        self,
        db,
        teacher_id,
    ):
        return await db.scalar(
            select(func.count())
            .select_from(ResultBatch)
            .where(ResultBatch.created_by == teacher_id)
        )

    async def count_class_students(
        self,
        db,
        class_id,
    ):
        return await db.scalar(
            select(func.count(func.distinct(StudentEnrollment.student_id))).where(
                StudentEnrollment.class_id == class_id
            )
        )

    async def count_class_subjects(
        self,
        db,
        class_id,
    ):
        return await db.scalar(
            select(func.count())
            .select_from(ClassSubject)
            .where(ClassSubject.class_id == class_id)
        )

    async def count_teacher_students(
        self,
        db,
        teacher_id,
    ):
        result = await db.scalar(
            select(func.count(func.distinct(StudentEnrollment.student_id)))
            .join(
                ClassTeacher,
                ClassTeacher.class_id == StudentEnrollment.class_id,
            )
            .where(ClassTeacher.teacher_id == teacher_id)
        )

        return result or 0

    async def count_teacher_classes(
        self,
        db,
        teacher_id,
    ):
        return await db.scalar(
            select(func.count())
            .select_from(ClassTeacher)
            .where(ClassTeacher.teacher_id == teacher_id)
        )

    async def get_teacher_classes(
        self,
        db,
        teacher_id,
    ):
        students_count = (
            select(func.count(StudentEnrollment.student_id))
            .where(StudentEnrollment.class_id == ClassTeacher.class_id)
            .correlate(ClassTeacher)
            .scalar_subquery()
        )

        subjects_count = (
            select(func.count(ClassSubject.subject_id))
            .where(ClassSubject.class_id == ClassTeacher.class_id)
            .correlate(ClassTeacher)
            .scalar_subquery()
        )

        result = await db.execute(
            select(
                ClassTeacher.class_id.label("id"),
                Class.name,
                Class.level,
                students_count.label("students_count"),
                subjects_count.label("subjects_count"),
            )
            .join(
                Class,
                Class.id == ClassTeacher.class_id,
            )
            .where(ClassTeacher.teacher_id == teacher_id)
            .order_by(Class.name)
        )

        return result.mappings().all()
