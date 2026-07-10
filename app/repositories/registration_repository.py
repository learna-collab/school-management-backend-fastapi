from sqlalchemy import select

from app.models.class_teacher import ClassTeacher
from app.models.classes import Class
from app.models.enrollment import StudentEnrollment
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

    async def create_student_enrollment(
        self,
        db,
        *,
        school_id,
        student_id,
        class_id,
    ):
        existing = await db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.student_id == student_id,
            )
        )

        enrollment = existing.scalar_one_or_none()

        if enrollment:
            enrollment.class_id = class_id
            enrollment.school_id = school_id

            await db.commit()
            await db.refresh(enrollment)

            return enrollment

        enrollment = StudentEnrollment(
            school_id=school_id,
            student_id=student_id,
            class_id=class_id,
        )

        db.add(enrollment)

        await db.commit()

        await db.refresh(enrollment)

        return enrollment

    async def assign_teacher_to_class(
        self,
        db,
        *,
        school_id,
        teacher_id,
        class_id,
    ):
        existing = await db.execute(
            select(ClassTeacher).where(
                ClassTeacher.teacher_id == teacher_id,
            )
        )

        assignment = existing.scalar_one_or_none()

        if assignment:
            assignment.class_id = class_id
            assignment.school_id = school_id

            await db.commit()
            await db.refresh(assignment)

            return assignment

        assignment = ClassTeacher(
            school_id=school_id,
            teacher_id=teacher_id,
            class_id=class_id,
        )

        db.add(assignment)

        await db.commit()
        await db.refresh(assignment)

        return assignment


registration_repo = RegistrationRepository()
