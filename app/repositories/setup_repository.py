from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic_template import AcademicTemplate
from app.models.class_subject import ClassSubject
from app.models.class_template import ClassTemplate
from app.models.classes import Class
from app.models.subject import Subject
from app.models.subject_template import SubjectTemplate
from app.models.template_class_subject import TemplateClassSubject


class AcademicSetupRepository:
    async def get_templates(
        self,
        db: AsyncSession,
    ):
        stmt = (
            select(AcademicTemplate)
            .where(AcademicTemplate.is_active.is_(True))
            .options(
                selectinload(AcademicTemplate.class_templates)
                .selectinload(ClassTemplate.subjects)
                .selectinload(TemplateClassSubject.subject_template)
            )
            .order_by(AcademicTemplate.name)
        )

        result = await db.execute(stmt)

        return result.scalars().unique().all()

    async def get_template(
        self,
        db: AsyncSession,
        template_id: UUID,
    ):
        stmt = (
            select(AcademicTemplate)
            .where(AcademicTemplate.id == template_id)
            .options(
                selectinload(AcademicTemplate.class_templates)
                .selectinload(ClassTemplate.subjects)
                .selectinload(TemplateClassSubject.subject_template)
            )
        )

        result = await db.execute(stmt)

        return result.unique().scalar_one_or_none()

    async def get_school_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        stmt = select(Class).where(Class.school_id == school_id)

        result = await db.execute(stmt)

        return result.scalars().all()

    async def get_school_subjects(
        self,
        db,
        school_id,
    ):
        stmt = select(Subject).where(Subject.school_id == school_id)

        result = await db.execute(stmt)

        return result.scalars().all()

    async def create_classes(
        self,
        db: AsyncSession,
        classes: list[Class],
    ):
        db.add_all(classes)

        await db.flush()

        return classes

    async def create_subjects(
        self,
        db,
        subjects,
    ):
        db.add_all(subjects)

        await db.flush()

        return subjects

    async def create_class_subjects(
        self,
        db,
        mappings,
    ):
        db.add_all(mappings)

        await db.flush()

        return mappings

    async def get_subject_by_name(
        self,
        db,
        school_id,
        name,
    ):
        stmt = select(Subject).where(
            Subject.school_id == school_id,
            Subject.name == name,
        )

        result = await db.execute(stmt)

        return result.scalar_one_or_none()

    async def get_class_by_name(
        self,
        db,
        school_id,
        name,
    ):
        stmt = select(Class).where(
            Class.school_id == school_id,
            Class.name == name,
        )

        result = await db.execute(stmt)

        return result.scalar_one_or_none()
