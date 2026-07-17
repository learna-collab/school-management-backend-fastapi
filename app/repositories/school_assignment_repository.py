from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_teacher import ClassTeacher
from app.models.enrollment import StudentEnrollment
from app.models.teacher import TeacherProfile
from app.models.teacher_class_subject import TeacherClassSubject
from app.models.user import User, UserRole


class SchoolAssignmentRepository:
    # ==========================================================
    # SCHOOL USERS
    # ==========================================================

    async def get_school_students(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        result = await db.execute(
            select(User)
            .where(
                and_(
                    User.school_id == school_id,
                    User.role == UserRole.STUDENT,
                )
            )
            .options(
                selectinload(User.credential),
                selectinload(User.credential),
                selectinload(User.enrollments).selectinload(
                    StudentEnrollment.school_class
                ),
            )
        )

        return result.scalars().all()

    async def get_school_teachers(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        result = await db.execute(
            select(User)
            .where(
                and_(
                    User.school_id == school_id,
                    User.role == UserRole.TEACHER,
                )
            )
            .options(
                selectinload(User.credential),
                selectinload(User.class_assignments).selectinload(
                    ClassTeacher.school_class
                ),
            )
        )

        return result.scalars().all()

    # ==========================================================
    # STUDENTS NOT IN CURRENT CLASS (ACTIVE SESSION)
    # ==========================================================

    async def get_school_students_not_in_class(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
        session_id: UUID,
    ):
        stmt = select(User).where(
            and_(
                User.school_id == school_id,
                User.role == UserRole.STUDENT,
                ~User.id.in_(
                    select(
                        StudentEnrollment.student_id,
                    ).where(
                        and_(
                            StudentEnrollment.class_id == class_id,
                            StudentEnrollment.session_id == session_id,
                        )
                    )
                ),
            )
        )

        result = await db.execute(stmt)

        return result.scalars().all()

    # ==========================================================
    # TEACHERS NOT ASSIGNED TO CLASS
    # ==========================================================

    async def get_school_teachers_not_in_class(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
    ):
        stmt = select(User).where(
            and_(
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
                ~User.id.in_(
                    select(
                        TeacherClassSubject.teacher_id,
                    ).where(
                        TeacherClassSubject.class_id == class_id,
                    )
                ),
            )
        )

        result = await db.execute(stmt)

        return result.scalars().all()

    # ==========================================================
    # STUDENT ENROLLMENT
    # ==========================================================
    async def get_student_enrollment(
        self,
        db: AsyncSession,
        student_id: UUID,
        session_id: UUID,
    ):
        result = await db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.session_id == session_id,
            ),
        )

        return result.scalar_one_or_none()

    async def get_unassigned_students(
        self,
        db: AsyncSession,
        school_id: UUID,
        session_id: UUID,
    ):
        enrolled_subquery = select(StudentEnrollment.student_id).where(
            StudentEnrollment.session_id == session_id,
        )

        result = await db.execute(
            select(User)
            .where(
                User.role == UserRole.STUDENT,
                User.school_id == school_id,
                User.id.not_in(enrolled_subquery),
            )
            .order_by(
                User.first_name,
                User.last_name,
            ),
        )

        return result.scalars().all()

    async def assign_student(
        self,
        db: AsyncSession,
        *,
        student_id: UUID,
        class_id: UUID,
        session_id: UUID,
        school_id: UUID,
    ):
        enrollment = StudentEnrollment(
            school_id=school_id,
            student_id=student_id,
            class_id=class_id,
            session_id=session_id,
            is_current=True,
        )

        db.add(enrollment)

        await db.commit()

        return enrollment

    async def remove_student_from_class(
        self,
        db: AsyncSession,
        *,
        student_id: UUID,
        class_id: UUID,
        session_id: UUID,
    ):
        stmt = delete(StudentEnrollment).where(
            and_(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.class_id == class_id,
                StudentEnrollment.session_id == session_id,
            )
        )

        result = await db.execute(stmt)

        await db.commit()

        return result.rowcount > 0

    # ==========================================================
    # CLASS STUDENTS
    # ==========================================================

    async def get_class_students(
        self,
        db: AsyncSession,
        class_id: UUID,
        session_id: UUID,
    ):
        result = await db.execute(
            select(User)
            .join(
                StudentEnrollment,
                StudentEnrollment.student_id == User.id,
            )
            .where(
                and_(
                    StudentEnrollment.class_id == class_id,
                    StudentEnrollment.session_id == session_id,
                )
            )
        )

        return result.scalars().all()

    # ==========================================================
    # CLASS TEACHERS
    # ==========================================================

    async def get_class_teachers(
        self,
        db: AsyncSession,
        class_id: UUID,
    ):
        result = await db.execute(
            select(User)
            .join(
                ClassTeacher,
                ClassTeacher.teacher_id == User.id,
            )
            .where(
                ClassTeacher.class_id == class_id,
            )
        )

        return result.scalars().all()

    # ==========================================================
    # ASSIGN TEACHER TO CLASS SUBJECT
    # ==========================================================
    async def remove_teacher_from_class(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        class_id: UUID,
    ):
        stmt = delete(ClassTeacher).where(
            ClassTeacher.teacher_id == teacher_id,
            ClassTeacher.class_id == class_id,
        )

        result = await db.execute(stmt)

        await db.commit()

        return result.rowcount > 0

    async def assign_teacher_to_class(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        class_id: UUID,
        school_id: UUID,
    ):
        assignment = ClassTeacher(
            school_id=school_id,
            teacher_id=teacher_id,
            class_id=class_id,
        )

        db.add(assignment)

        await db.commit()

        await db.refresh(assignment)

        return assignment

    async def assign_teacher(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ):
        assignment = TeacherClassSubject(
            school_id=school_id,
            teacher_id=teacher_id,
            class_id=class_id,
            subject_id=subject_id,
        )

        db.add(assignment)

        await db.commit()

        return assignment

    async def remove_teacher_assignment(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        class_id: UUID,
        subject_id: UUID,
    ):
        stmt = delete(TeacherClassSubject).where(
            and_(
                TeacherClassSubject.teacher_id == teacher_id,
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.subject_id == subject_id,
            )
        )

        result = await db.execute(stmt)

        await db.commit()

        return result.rowcount > 0

    async def get_class_assignments(
        self,
        db: AsyncSession,
        class_id: UUID,
    ):
        result = await db.execute(
            select(TeacherClassSubject)
            .options(
                selectinload(TeacherClassSubject.teacher).selectinload(
                    TeacherProfile.user
                ),
                selectinload(TeacherClassSubject.subject),
            )
            .where(
                TeacherClassSubject.class_id == class_id,
            )
        )

        return result.scalars().all()

    async def promote_students(
        self,
        db: AsyncSession,
        *,
        from_class_id: UUID,
        to_class_id: UUID,
        from_session_id: UUID,
        to_session_id: UUID,
    ):
        result = await db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.class_id == from_class_id,
                StudentEnrollment.session_id == from_session_id,
            )
        )

        enrollments = result.scalars().all()

        count = 0

        for enrollment in enrollments:
            exists = await db.execute(
                select(StudentEnrollment).where(
                    StudentEnrollment.student_id == enrollment.student_id,
                    StudentEnrollment.session_id == to_session_id,
                )
            )

            if exists.scalar_one_or_none():
                continue

            db.add(
                StudentEnrollment(
                    school_id=enrollment.school_id,
                    student_id=enrollment.student_id,
                    class_id=to_class_id,
                    session_id=to_session_id,
                    is_current=True,
                )
            )

            enrollment.is_current = False

            count += 1

        await db.commit()

        return count


school_assignment_repo = SchoolAssignmentRepository()
