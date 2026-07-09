from uuid import UUID

from sqlalchemy import delete, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_subject import ClassSubject
from app.models.classes import Class
from app.models.subject import Subject
from app.models.teacher_class_subject import TeacherClassSubject
from app.models.user import User, UserRole


class AssignmentRepository:
    # =====================================================
    # SETUP DATA
    # =====================================================

    async def get_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
    ) -> list[Class]:
        result = await db.execute(
            select(Class)
            .where(Class.school_id == school_id)
            .order_by(
                Class.sort_order,
                Class.name,
            )
        )

        return result.scalars().all()

    async def get_subjects(
        self,
        db: AsyncSession,
    ) -> list[Subject]:
        result = await db.execute(select(Subject).order_by(Subject.name))

        return result.scalars().all()

    async def get_teachers(
        self,
        db: AsyncSession,
        school_id: UUID,
    ) -> list[User]:
        result = await db.execute(
            select(User)
            .where(
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
                User.is_active.is_(True),
            )
            .order_by(
                User.first_name,
                User.last_name,
            )
        )

        return result.scalars().all()

    # =====================================================
    # CLASS
    # =====================================================

    async def get_class(
        self,
        db: AsyncSession,
        class_id: UUID,
        school_id: UUID,
    ) -> Class | None:
        result = await db.execute(
            select(Class).where(
                Class.id == class_id,
                Class.school_id == school_id,
            )
        )

        return result.scalar_one_or_none()

    # =====================================================
    # SUBJECT
    # =====================================================

    async def get_subject(
        self,
        db: AsyncSession,
        subject_id: UUID,
    ) -> Subject | None:
        result = await db.execute(
            select(Subject).where(
                Subject.id == subject_id,
            )
        )

        return result.scalar_one_or_none()

    # =====================================================
    # TEACHER
    # =====================================================

    async def get_teacher(
        self,
        db: AsyncSession,
        teacher_id: UUID,
        school_id: UUID,
    ) -> User | None:
        result = await db.execute(
            select(User).where(
                User.id == teacher_id,
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
            )
        )

        return result.scalar_one_or_none()

    # =====================================================
    # EXISTS
    # =====================================================

    async def class_subject_exists(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ) -> bool:
        result = await db.execute(
            select(ClassSubject.id).where(
                ClassSubject.class_id == class_id,
                ClassSubject.subject_id == subject_id,
                ClassSubject.school_id == school_id,
            )
        )

        return result.scalar_one_or_none() is not None

    async def teacher_assignment_exists(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
        teacher_id: UUID,
        school_id: UUID,
    ) -> bool:
        result = await db.execute(
            select(TeacherClassSubject.id).where(
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.subject_id == subject_id,
                TeacherClassSubject.teacher_id == teacher_id,
                TeacherClassSubject.school_id == school_id,
            )
        )

        return result.scalar_one_or_none() is not None

    # =====================================================
    # CREATE
    # =====================================================

    async def create_class_subject(
        self,
        db: AsyncSession,
        *,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ) -> ClassSubject:
        obj = ClassSubject(
            class_id=class_id,
            subject_id=subject_id,
            school_id=school_id,
        )

        db.add(obj)

        return obj

    async def create_teacher_assignment(
        self,
        db: AsyncSession,
        *,
        class_id: UUID,
        subject_id: UUID,
        teacher_id: UUID,
        school_id: UUID,
    ) -> TeacherClassSubject:
        obj = TeacherClassSubject(
            class_id=class_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            school_id=school_id,
        )

        db.add(obj)

        return obj

    # =====================================================
    # GET ASSIGNMENTS
    # =====================================================

    async def get_class_assignments(
        self,
        db: AsyncSession,
        class_id: UUID,
        school_id: UUID,
    ) -> list[TeacherClassSubject]:
        result = await db.execute(
            select(TeacherClassSubject)
            .options(
                selectinload(TeacherClassSubject.subject),
                selectinload(TeacherClassSubject.teacher),
                selectinload(TeacherClassSubject.school_class),
            )
            .where(
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.school_id == school_id,
            )
        )

        return result.scalars().all()

    # =====================================================
    # UPDATE
    # =====================================================

    async def get_teacher_assignment(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ) -> TeacherClassSubject | None:
        result = await db.execute(
            select(TeacherClassSubject).where(
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.subject_id == subject_id,
                TeacherClassSubject.school_id == school_id,
            )
        )

        return result.scalar_one_or_none()

    async def update_teacher_assignment(
        self,
        assignment: TeacherClassSubject,
        teacher_id: UUID,
    ) -> TeacherClassSubject:
        assignment.teacher_id = teacher_id

        return assignment

    # =====================================================
    # DELETE
    # =====================================================

    async def delete_teacher_assignment(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ):
        await db.execute(
            delete(TeacherClassSubject).where(
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.subject_id == subject_id,
                TeacherClassSubject.school_id == school_id,
            )
        )

    async def delete_class_subject(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ):
        await db.execute(
            delete(ClassSubject).where(
                ClassSubject.class_id == class_id,
                ClassSubject.subject_id == subject_id,
                ClassSubject.school_id == school_id,
            )
        )
        # =====================================================

    # DELETE ALL CLASS ASSIGNMENTS
    # =====================================================

    async def delete_all_teacher_assignments(
        self,
        db: AsyncSession,
        class_id: UUID,
        school_id: UUID,
    ):
        await db.execute(
            delete(TeacherClassSubject).where(
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.school_id == school_id,
            )
        )

    async def delete_all_class_subjects(
        self,
        db: AsyncSession,
        class_id: UUID,
        school_id: UUID,
    ):
        await db.execute(
            delete(ClassSubject).where(
                ClassSubject.class_id == class_id,
                ClassSubject.school_id == school_id,
            )
        )

        # =====================================================

    # BULK SUBJECTS
    # =====================================================

    async def get_subjects_by_ids(
        self,
        db: AsyncSession,
        subject_ids: list[UUID],
    ) -> list[Subject]:
        if not subject_ids:
            return []

        result = await db.execute(select(Subject).where(Subject.id.in_(subject_ids)))

        return result.scalars().all()

    # =====================================================
    # BULK TEACHERS
    # =====================================================

    async def get_teachers_by_ids(
        self,
        db: AsyncSession,
        school_id: UUID,
        teacher_ids: list[UUID],
    ) -> list[User]:
        if not teacher_ids:
            return []

        result = await db.execute(
            select(User).where(
                User.id.in_(teacher_ids),
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
                User.is_active.is_(True),
            )
        )

        return result.scalars().all()

    # =====================================================
    # EXISTING ASSIGNMENTS
    # =====================================================

    async def get_existing_assignments(
        self,
        db: AsyncSession,
        class_id: UUID,
        school_id: UUID,
    ) -> list[TeacherClassSubject]:
        result = await db.execute(
            select(TeacherClassSubject)
            .options(
                selectinload(TeacherClassSubject.subject),
                selectinload(TeacherClassSubject.teacher),
            )
            .where(
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.school_id == school_id,
            )
        )

        return result.scalars().all()

    # =====================================================
    # DELETE ASSIGNMENTS NOT IN PAYLOAD
    # =====================================================

    async def delete_assignments_not_in_subjects(
        self,
        db: AsyncSession,
        class_id: UUID,
        school_id: UUID,
        subject_ids: list[UUID],
    ):
        if not subject_ids:
            await db.execute(
                delete(TeacherClassSubject).where(
                    TeacherClassSubject.class_id == class_id,
                    TeacherClassSubject.school_id == school_id,
                )
            )

            await db.execute(
                delete(ClassSubject).where(
                    ClassSubject.class_id == class_id,
                    ClassSubject.school_id == school_id,
                )
            )

            return

        await db.execute(
            delete(TeacherClassSubject).where(
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.school_id == school_id,
                not_(TeacherClassSubject.subject_id.in_(subject_ids)),
            )
        )

        await db.execute(
            delete(ClassSubject).where(
                ClassSubject.class_id == class_id,
                ClassSubject.school_id == school_id,
                not_(ClassSubject.subject_id.in_(subject_ids)),
            )
        )

    # =====================================================
    # BULK CLASS SUBJECTS
    # =====================================================

    async def get_existing_class_subjects(
        self,
        db: AsyncSession,
        class_id: UUID,
        school_id: UUID,
    ) -> list[ClassSubject]:
        result = await db.execute(
            select(ClassSubject).where(
                ClassSubject.class_id == class_id,
                ClassSubject.school_id == school_id,
            )
        )

        return result.scalars().all()

    async def get_existing_assignment(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ) -> TeacherClassSubject | None:
        result = await db.execute(
            select(TeacherClassSubject).where(
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.subject_id == subject_id,
                TeacherClassSubject.school_id == school_id,
            )
        )

        return result.scalar_one_or_none()

    # =====================================================

    # FLUSH
    # =====================================================

    async def flush(
        self,
        db: AsyncSession,
    ):
        await db.flush()

    async def delete_teacher_assignment_by_subject(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ):
        await db.execute(
            delete(TeacherClassSubject).where(
                TeacherClassSubject.class_id == class_id,
                TeacherClassSubject.subject_id == subject_id,
                TeacherClassSubject.school_id == school_id,
            )
        )

    async def delete_class_subject_by_subject(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ):
        await db.execute(
            delete(ClassSubject).where(
                ClassSubject.class_id == class_id,
                ClassSubject.subject_id == subject_id,
                ClassSubject.school_id == school_id,
            )
        )
