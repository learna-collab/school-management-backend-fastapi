from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_subject import ClassSubject
from app.models.classes import Class
from app.models.subject import Subject


class SubjectRepository:
    async def create(
        self,
        db: AsyncSession,
        subject: Subject,
    ):
        db.add(subject)

        await db.commit()

        await db.refresh(subject)

        return subject

    async def get_school_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        result = await db.execute(
            select(Subject)
            .where(
                Subject.school_id == school_id,
            )
            .order_by(
                Subject.name,
            )
        )

        return result.scalars().all()

    async def get_by_id(
        self,
        db: AsyncSession,
        subject_id: UUID,
    ):
        return await db.get(
            Subject,
            subject_id,
        )

    # ==================================================
    # CLASS SUBJECTS
    # ==================================================

    async def assign_subject_to_class(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
    ):
        assignment = ClassSubject(
            class_id=class_id,
            subject_id=subject_id,
        )

        db.add(assignment)

        await db.commit()

        await db.refresh(assignment)

        return assignment

    async def get_class_subjects(
        self,
        db: AsyncSession,
        class_id: UUID,
        school_id: UUID,
    ):
        result = await db.execute(
            select(Subject)
            .join(
                ClassSubject,
                ClassSubject.subject_id == Subject.id,
            )
            .join(
                Class,
                Class.id == ClassSubject.class_id,
            )
            .where(
                Class.id == class_id,
                Class.school_id == school_id,
            )
            .order_by(
                Subject.name,
            )
        )

        return result.scalars().all()

    async def get_class_subject_assignment(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
    ):
        result = await db.execute(
            select(ClassSubject).where(
                ClassSubject.class_id == class_id,
                ClassSubject.subject_id == subject_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_school_subject(
        self,
        db: AsyncSession,
        subject_id: UUID,
        school_id: UUID,
    ):
        result = await db.execute(
            select(Subject).where(
                Subject.id == subject_id,
                Subject.school_id == school_id,
            )
        )

        return result.scalar_one_or_none()

    async def remove_subject_from_class(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
    ):
        assignment = await self.get_class_subject_assignment(
            db=db,
            class_id=class_id,
            subject_id=subject_id,
        )

        if not assignment:
            return False

        await db.delete(assignment)

        await db.commit()

        return True

    async def subject_assigned_to_class(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
    ):
        result = await db.execute(
            select(ClassSubject).where(
                ClassSubject.class_id == class_id,
                ClassSubject.subject_id == subject_id,
            )
        )

        return result.scalar_one_or_none()


subject_repository = SubjectRepository()
