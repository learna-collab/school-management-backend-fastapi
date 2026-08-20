from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic_session import AcademicSession
from app.models.class_teacher import ClassTeacher
from app.models.classes import Class
from app.models.lesson import Lesson
from app.models.lesson_alf import LessonALF
from app.models.subject import Subject
from app.models.subject_template import SubjectTemplate
from app.models.template_class_subject import TemplateClassSubject
from app.models.terms import Term


class LessonRepository:
    # =========================
    # CREATE / DELETE
    # =========================

    async def create(self, db: AsyncSession, lesson: Lesson) -> Lesson:
        db.add(lesson)
        await db.flush()
        await db.refresh(lesson)
        return lesson

    async def create_alf(self, db: AsyncSession, alf: LessonALF) -> LessonALF:
        db.add(alf)
        await db.flush()
        await db.refresh(alf)
        return alf

    async def delete(self, db: AsyncSession, lesson_id: UUID):
        lesson = await db.get(Lesson, lesson_id)

        if lesson:
            await db.delete(lesson)
            await db.commit()

    # =========================
    # INTERNAL HELPER
    # =========================

    def _lesson_to_dict(self, lesson, class_name: str, subject_name: str):
        return {
            "id": str(lesson.id),
            "week_number": lesson.week_number,
            "class_name": class_name,
            "subject_name": subject_name,
            "title": lesson.title,
            "topic": lesson.topic,
            "objectives": lesson.objectives,
            "teacher_notes": lesson.teacher_notes,
            "file_url": lesson.file_url,
            "is_published": lesson.is_published,
            "alf": lesson.alf,
        }

    # =========================
    # SUPER ADMIN LIST
    # =========================

    async def get_lessons(
        self,
        db: AsyncSession,
        *,
        class_template_id: UUID,
        subject_template_id: UUID,
        session_id: UUID,
        term_id: UUID,
        week_number: int | None = None,
    ):
        query = (
            select(Lesson)
            .options(
                selectinload(Lesson.alf),
                selectinload(Lesson.class_template),
                selectinload(Lesson.subject_template),
            )
            .where(
                Lesson.class_template_id == class_template_id,
                Lesson.subject_template_id == subject_template_id,
                Lesson.session_id == session_id,
                Lesson.term_id == term_id,
            )
            .order_by(Lesson.week_number.asc())
        )

        if week_number is not None:
            query = query.where(Lesson.week_number == week_number)

        result = await db.execute(query)
        lessons = result.scalars().all()

        return [
            self._lesson_to_dict(
                lesson,
                lesson.class_template.name if lesson.class_template else "",
                lesson.subject_template.name if lesson.subject_template else "",
            )
            for lesson in lessons
        ]

    # =========================
    # SCHOOL ADMIN LIST
    # =========================

    async def get_school_lessons(
        self,
        db: AsyncSession,
        *,
        school_id: UUID,
        class_id: UUID,
        subject_id: UUID,
        session_id: UUID,
        term_id: UUID,
        week_number: int | None = None,
    ):
        # School class
        class_result = await db.execute(
            select(Class).where(
                Class.id == class_id,
                Class.school_id == school_id,
            )
        )

        school_class = class_result.scalar_one_or_none()

        if not school_class:
            return []

        # Custom classes currently have no generic lessons
        if school_class.is_custom or not school_class.template_class_id:
            return []

        # School subject
        subject_result = await db.execute(
            select(Subject).where(
                Subject.id == subject_id,
                Subject.school_id == school_id,
            )
        )

        school_subject = subject_result.scalar_one_or_none()

        if not school_subject or not school_subject.template_subject_id:
            return []

        query = (
            select(Lesson)
            .options(selectinload(Lesson.alf))
            .where(
                Lesson.class_template_id == school_class.template_class_id,
                Lesson.subject_template_id == school_subject.template_subject_id,
                Lesson.session_id == session_id,
                Lesson.term_id == term_id,
                Lesson.is_published.is_(True),
            )
            .order_by(Lesson.week_number.asc())
        )

        if week_number is not None:
            query = query.where(Lesson.week_number == week_number)

        result = await db.execute(query)
        lessons = result.scalars().all()

        return [
            self._lesson_to_dict(
                lesson,
                school_class.name,
                school_subject.name,
            )
            for lesson in lessons
        ]

    # =========================
    # TEACHER LIST
    # =========================

    async def get_teacher_lessons(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        class_id: UUID,
        subject_id: UUID,
        session_id: UUID,
        term_id: UUID,
        week_number: int | None = None,
    ):
        class_result = await db.execute(select(Class).where(Class.id == class_id))
        school_class = class_result.scalar_one_or_none()

        if not school_class or not school_class.template_class_id:
            return []

        subject_result = await db.execute(
            select(Subject).where(Subject.id == subject_id)
        )
        school_subject = subject_result.scalar_one_or_none()

        if not school_subject or not school_subject.template_subject_id:
            return []

        # Validate teacher is assigned to this class
        assignment_result = await db.execute(
            select(ClassTeacher).where(
                ClassTeacher.teacher_id == teacher_id,
                ClassTeacher.class_id == class_id,
            )
        )

        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            return []

        query = (
            select(Lesson)
            .options(selectinload(Lesson.alf))
            .where(
                Lesson.class_template_id == school_class.template_class_id,
                Lesson.subject_template_id == school_subject.template_subject_id,
                Lesson.session_id == session_id,
                Lesson.term_id == term_id,
                Lesson.is_published.is_(True),
            )
            .order_by(
                Lesson.week_number.asc(),
            )
        )

        if week_number is not None:
            query = query.where(Lesson.week_number == week_number)

        result = await db.execute(query)
        lessons = result.scalars().all()

        return [
            self._lesson_to_dict(
                lesson,
                school_class.name,
                school_subject.name,
            )
            for lesson in lessons
        ]

    # =========================
    # SINGLE LESSON
    # =========================

    async def get_by_id(self, db: AsyncSession, lesson_id: UUID):
        result = await db.execute(
            select(Lesson)
            .options(
                selectinload(Lesson.alf),
                selectinload(Lesson.class_template),
                selectinload(Lesson.subject_template),
            )
            .where(Lesson.id == lesson_id)
        )

        lesson = result.scalar_one_or_none()

        if not lesson:
            return None

        return self._lesson_to_dict(
            lesson,
            lesson.class_template.name if lesson.class_template else "",
            lesson.subject_template.name if lesson.subject_template else "",
        )

    async def get_school_lesson_by_id(
        self,
        db: AsyncSession,
        *,
        school_id: UUID,
        lesson_id: UUID,
    ):
        return await self.get_by_id(db, lesson_id)

    async def get_teacher_lesson_by_id(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        lesson_id: UUID,
    ):
        return await self.get_by_id(db, lesson_id)

    # =========================
    # FILTER DROPDOWNS
    # =========================

    async def get_all_classes(self, db: AsyncSession):
        result = await db.execute(
            select(Class)
            .where(Class.template_class_id.isnot(None))
            .order_by(Class.name.asc())
        )

        classes = result.scalars().all()

        seen = set()
        data = []

        for item in classes:
            if item.template_class_id in seen:
                continue

            seen.add(item.template_class_id)

            data.append(
                {
                    "id": str(item.template_class_id),
                    "name": item.name,
                }
            )

        return data

    async def get_all_subjects(self, db: AsyncSession):
        result = await db.execute(
            select(Subject)
            .where(Subject.template_subject_id.isnot(None))
            .order_by(Subject.name.asc())
        )

        subjects = result.scalars().all()

        seen = set()
        data = []

        for item in subjects:
            if item.template_subject_id in seen:
                continue

            seen.add(item.template_subject_id)

            data.append(
                {
                    "id": str(item.template_subject_id),
                    "name": item.name,
                }
            )

        return data

    async def get_all_unique_sessions(self, db: AsyncSession):
        result = await db.execute(
            select(AcademicSession).order_by(AcademicSession.name.asc())
        )

        sessions = result.scalars().all()

        return [{"id": str(item.id), "name": item.name} for item in sessions]

    async def get_all_unique_terms(self, db: AsyncSession):
        result = await db.execute(select(Term).order_by(Term.name.asc()))

        terms = result.scalars().all()

        return [{"id": str(item.id), "name": item.name} for item in terms]

    async def get_subjects_by_class_template(
        self,
        db: AsyncSession,
        class_template_id: UUID,
    ):
        result = await db.execute(
            select(SubjectTemplate)
            .join(
                TemplateClassSubject,
                TemplateClassSubject.subject_template_id == SubjectTemplate.id,
            )
            .where(
                TemplateClassSubject.class_template_id == class_template_id,
                SubjectTemplate.is_active.is_(True),
            )
            .order_by(SubjectTemplate.name.asc())
        )

        subjects = result.scalars().all()

        return [
            {
                "id": str(item.id),
                "name": item.name,
            }
            for item in subjects
        ]
