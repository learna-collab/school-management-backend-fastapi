from uuid import UUID

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.class_subject import ClassSubject
from app.models.class_teacher import ClassTeacher
from app.models.enrollment import StudentEnrollment
from app.models.student import StudentProfile
from app.models.subject import Subject
from app.models.teacher import TeacherProfile
from app.models.teacher_class_subject import TeacherClassSubject


class TeacherAssignmentRepository:
    async def teacher_can_manage_class(
        self,
        db: AsyncSession,
        teacher_id,
        class_id,
    ) -> bool:
        return await db.scalar(
            select(
                exists().where(
                    ClassTeacher.teacher_id == teacher_id,
                    ClassTeacher.class_id == class_id,
                )
            )
        )

    async def get_teacher_profile(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> TeacherProfile | None:
        result = await db.execute(
            select(TeacherProfile).where(
                TeacherProfile.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_teacher_classes(
        self,
        db: AsyncSession,
        teacher_user_id,
    ):
        result = await db.execute(
            select(
                TeacherClassSubject.class_id,
            )
            .join(
                TeacherProfile,
                TeacherProfile.id == TeacherClassSubject.teacher_id,
            )
            .where(
                TeacherProfile.user_id == teacher_user_id,
            )
        )

        return result.scalars().all()

    async def get_teacher_assignments(
        self,
        db: AsyncSession,
        teacher_user_id,
    ):
        result = await db.execute(
            select(
                TeacherClassSubject,
            )
            .join(
                TeacherProfile,
                TeacherProfile.id == TeacherClassSubject.teacher_id,
            )
            .where(
                TeacherProfile.user_id == teacher_user_id,
            )
        )

        return result.scalars().all()

    async def get_students_by_class(
        self,
        db,
        class_id,
        session_id,
        term_id,
    ):
        result = await db.execute(
            select(StudentProfile)
            .join(
                StudentEnrollment,
                StudentEnrollment.student_id == StudentProfile.user_id,
            )
            .where(
                StudentEnrollment.class_id == class_id,
                StudentEnrollment.session_id == session_id,
            )
            .options(
                joinedload(StudentProfile.user),
            )
            .order_by(
                StudentProfile.admission_number,
            )
        )

        return result.scalars().unique().all()

    async def get_teacher_subjects(
        self,
        db,
        teacher_id,
        class_id,
    ):
        result = await db.execute(
            select(TeacherClassSubject)
            .where(
                TeacherClassSubject.teacher_id == teacher_id,
                TeacherClassSubject.class_id == class_id,
            )
            .options(joinedload(TeacherClassSubject.subject))
        )

        return result.scalars().all()

    async def get_class_subjects(
        self,
        db,
        class_id,
    ):
        result = await db.execute(
            select(ClassSubject)
            .where(ClassSubject.class_id == class_id)
            .options(joinedload(ClassSubject.subject))
            .order_by(ClassSubject.created_at)
        )

        return result.scalars().all()

    async def teacher_has_class_access(
        self,
        db,
        teacher_id,
        class_id,
    ):
        print("teacher_id:", teacher_id)
        print("class_id:", class_id)
        result = await db.execute(
            select(ClassTeacher.id).where(
                ClassTeacher.teacher_id == teacher_id,
                ClassTeacher.class_id == class_id,
            )
        )

        return result.scalar_one_or_none() is not None


teacher_assignment_repository = TeacherAssignmentRepository()
