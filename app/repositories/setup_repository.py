from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic_template import AcademicTemplate
from app.models.class_subject import ClassSubject
from app.models.class_template import ClassTemplate
from app.models.classes import Class
from app.models.subject import Subject
from app.models.template_class_subject import TemplateClassSubject


class AcademicSetupRepository:
    # =====================================================
    # TEMPLATE
    # =====================================================

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

    async def get_all_template_classes(
        self,
        db: AsyncSession,
    ):
        stmt = (
            select(ClassTemplate)
            .options(
                selectinload(ClassTemplate.subjects).selectinload(
                    TemplateClassSubject.subject_template
                )
            )
            .order_by(
                ClassTemplate.level,
                ClassTemplate.sort_order,
                ClassTemplate.name,
            )
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

    async def get_template_classes(
        self,
        db: AsyncSession,
        levels: list[str],
    ):
        stmt = (
            select(ClassTemplate)
            .where(
                ClassTemplate.level.in_(levels),
            )
            .options(
                selectinload(ClassTemplate.subjects).selectinload(
                    TemplateClassSubject.subject_template
                )
            )
            .order_by(
                ClassTemplate.level,
                ClassTemplate.sort_order,
                ClassTemplate.name,
            )
        )

        result = await db.execute(stmt)

        return result.scalars().unique().all()

    # =====================================================
    # SCHOOL SETUP
    # =====================================================

    async def get_school_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        stmt = (
            select(Class)
            .where(Class.school_id == school_id)
            .options(
                selectinload(Class.class_subjects).selectinload(ClassSubject.subject)
            )
            .order_by(
                Class.sort_order,
                Class.name,
            )
        )

        result = await db.execute(stmt)
        return result.scalars().unique().all()

    async def get_school_classes_with_mappings(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        """
        Return only classes that are part of the CURRENT
        academic configuration.

        A class remains stored after a reset because it may be
        referenced by historical records such as:

        - student enrollments
        - results
        - attendance
        - lessons
        - other academic records

        Therefore, existence of a Class record does NOT mean that
        the class is currently configured.

        A class is considered currently configured only when it has
        at least one ClassSubject mapping.
        """

        stmt = (
            select(Class)
            .where(
                Class.school_id == school_id,
                Class.class_subjects.any(),
            )
            .options(
                selectinload(Class.class_subjects).selectinload(ClassSubject.subject)
            )
            .order_by(
                Class.sort_order,
                Class.name,
            )
        )

        result = await db.execute(stmt)
        return result.scalars().unique().all()

    async def get_school_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        stmt = (
            select(Subject).where(Subject.school_id == school_id).order_by(Subject.name)
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    # =====================================================
    # CREATE
    # =====================================================

    async def create_class(
        self,
        db: AsyncSession,
        school_class: Class,
    ):
        db.add(school_class)
        await db.flush()
        await db.refresh(school_class)
        return school_class

    async def create_subject(
        self,
        db: AsyncSession,
        subject: Subject,
    ):
        db.add(subject)
        await db.flush()
        await db.refresh(subject)
        return subject

    async def create_mapping(
        self,
        db: AsyncSession,
        mapping: ClassSubject,
    ):
        db.add(mapping)
        await db.flush()
        return mapping

    async def bulk_create_classes(
        self,
        db: AsyncSession,
        classes: list[Class],
    ):
        db.add_all(classes)
        await db.flush()
        return classes

    async def bulk_create_subjects(
        self,
        db: AsyncSession,
        subjects: list[Subject],
    ):
        db.add_all(subjects)
        await db.flush()
        return subjects

    async def bulk_create_mappings(
        self,
        db: AsyncSession,
        mappings: list[ClassSubject],
    ):
        db.add_all(mappings)
        await db.flush()
        return mappings

    # =====================================================
    # FINDERS
    # =====================================================

    async def get_class(
        self,
        db: AsyncSession,
        class_id: UUID,
    ):
        stmt = select(Class).where(Class.id == class_id)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subject(
        self,
        db: AsyncSession,
        subject_id: UUID,
    ):
        stmt = select(Subject).where(Subject.id == subject_id)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subject_by_name(
        self,
        db: AsyncSession,
        school_id: UUID,
        name: str,
    ):
        stmt = select(Subject).where(
            Subject.school_id == school_id,
            Subject.name == name,
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_class_by_name(
        self,
        db: AsyncSession,
        school_id: UUID,
        name: str,
    ):
        stmt = select(Class).where(
            Class.school_id == school_id,
            Class.name == name,
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # =====================================================
    # UPDATE
    # =====================================================

    async def update_class(
        self,
        db: AsyncSession,
        school_class: Class,
    ):
        await db.flush()
        await db.refresh(school_class)
        return school_class

    async def update_subject(
        self,
        db: AsyncSession,
        subject: Subject,
    ):
        await db.flush()
        await db.refresh(subject)
        return subject

    # =====================================================
    # DELETE
    # =====================================================

    async def delete_class(
        self,
        db: AsyncSession,
        school_class: Class,
    ):
        await db.delete(school_class)

    async def delete_subject(
        self,
        db: AsyncSession,
        subject: Subject,
    ):
        await db.delete(subject)

    async def remove_class_subjects(
        self,
        db: AsyncSession,
        class_id: UUID,
    ):
        stmt = delete(ClassSubject).where(ClassSubject.class_id == class_id)

        await db.execute(stmt)

    async def remove_subject_mappings(
        self,
        db: AsyncSession,
        subject_id: UUID,
    ):
        stmt = delete(ClassSubject).where(ClassSubject.subject_id == subject_id)

        await db.execute(stmt)

    # =====================================================
    # RESET SCHOOL SETUP
    # =====================================================

    async def delete_school_mappings(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        """
        Remove class-subject relationships for the school.

        IMPORTANT:

        We intentionally do NOT delete classes or subjects here.

        Classes may be referenced by:
            - student_enrollments
            - attendance
            - lessons
            - results
            - other academic records

        Subjects may be referenced by:
            - result_records
            - lessons
            - class_subjects
            - other academic records
        """

        stmt = delete(ClassSubject).where(ClassSubject.school_id == school_id)

        await db.execute(stmt)

    async def delete_school_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        """
        DEPRECATED FOR RESET OPERATIONS.

        Subjects must not be bulk-deleted because existing
        result records and other academic records may reference them.

        This method is intentionally left as a no-op so existing
        callers do not accidentally destroy historical data.
        """

        return None

    async def delete_school_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        """
        DEPRECATED FOR RESET OPERATIONS.

        Classes must not be bulk-deleted because existing
        student enrollments and other academic records may reference them.

        This method is intentionally left as a no-op so existing
        callers do not accidentally destroy historical data.
        """

        return None

    async def get_school_subjects_with_mappings(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        stmt = (
            select(Subject)
            .where(Subject.school_id == school_id)
            .options(selectinload(Subject.class_subjects))
        )

        result = await db.execute(stmt)
        return result.scalars().unique().all()

    async def get_class_subject(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
    ):
        stmt = select(ClassSubject).where(
            ClassSubject.class_id == class_id,
            ClassSubject.subject_id == subject_id,
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # =====================================================
    # CLASS SUBJECT SYNC
    # =====================================================

    async def get_class_mappings(
        self,
        db: AsyncSession,
        class_id: UUID,
    ):
        stmt = select(ClassSubject).where(ClassSubject.class_id == class_id)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def delete_mapping(
        self,
        db: AsyncSession,
        mapping: ClassSubject,
    ):
        await db.delete(mapping)

    async def get_class_by_template_id(
        self,
        db: AsyncSession,
        school_id: UUID,
        template_class_id: UUID,
    ):
        stmt = select(Class).where(
            Class.school_id == school_id,
            Class.template_class_id == template_class_id,
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subject_by_template_id(
        self,
        db: AsyncSession,
        school_id: UUID,
        template_subject_id: UUID,
    ):
        stmt = select(Subject).where(
            Subject.school_id == school_id,
            Subject.template_subject_id == template_subject_id,
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # =====================================================
    # RESET ENTIRE SCHOOL SETUP
    # =====================================================

    async def clear_school_setup(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        """
        Safely reset the school's academic configuration.

        We only remove ClassSubject mappings.

        We DO NOT delete:
            - Classes
            - Subjects

        Existing classes and subjects can already be referenced by:
        student enrollments, result records, attendance, lessons,
        and other historical academic data.

        Deleting them would cause foreign-key violations and,
        more importantly, would destroy the identity of historical
        academic records.
        """

        await self.delete_school_mappings(
            db,
            school_id,
        )

        await db.flush()
