import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import Lesson
from app.models.lesson_alf import LessonALF
from app.models.subject_template import SubjectTemplate
from app.repositories.lesson_repository import LessonRepository
from app.services.cloudinary_service import cloudinary_service
from app.services.lesson_parser import LessonParser


class LessonService:
    def __init__(self):
        self.repository = LessonRepository()
        self.parser = LessonParser()

    async def upload_lesson(
        self,
        *,
        db: AsyncSession,
        created_by: UUID,
        class_template_id: UUID,
        subject_template_id: UUID,
        session_id: UUID,
        term_id: UUID,
        week_number: int,
        file: UploadFile,
    ):
        # keep original extension (.pdf, .docx, etc.)
        suffix = Path(file.filename).suffix.lower()

        # Get subject name from database
        subject = await db.get(SubjectTemplate, subject_template_id)

        subject_name = subject.name.replace(" ", "-") if subject else "Subject"

        contents = await file.read()

        # Upload original file to Cloudinary
        upload_result = await cloudinary_service.upload_bytes(
            contents=contents,
            filename=file.filename,
            folder="lessons/daily",
            public_id=f"Week-{week_number}-{subject_name}{suffix}",
            resource_type="raw",
        )

        file_url = upload_result["url"]

        # Save temporarily for parsing
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp:
            temp.write(contents)
            temp_path = temp.name

        # Parse lesson note
        parsed = await self.parser.parse(
            file_path=temp_path,
            week_number=week_number,
        )

        # Create lesson
        lesson = Lesson(
            created_by=created_by,
            class_template_id=class_template_id,
            subject_template_id=subject_template_id,
            session_id=session_id,
            term_id=term_id,
            week_number=parsed.week_number,
            title=parsed.title or "Untitled Lesson",
            topic=parsed.topic or parsed.title or "Untitled Lesson",
            objectives=(parsed.objectives or "Objectives not extracted from document."),
            teacher_notes=parsed.teacher_notes,
            file_url=file_url,
        )

        lesson = await self.repository.create(db, lesson)

        alf = LessonALF(
            lesson_id=lesson.id,
            independent_reading=parsed.alf.independent_reading,
            mini_lesson=parsed.alf.mini_lesson,
            case_study=parsed.alf.case_study,
            project_based_learning=parsed.alf.project_based_learning,
            evaluation=parsed.alf.evaluation,
        )

        await self.repository.create_alf(db, alf)

        await db.commit()

        lesson = await self.repository.get_by_id(db, lesson.id)

        return lesson

    async def get_lesson(
        self,
        db: AsyncSession,
        lesson_id: UUID,
    ):
        return await self.repository.get_by_id(db, lesson_id)

    async def get_classes(self, db: AsyncSession):
        return await self.repository.get_all_classes(db)

    async def get_subjects(self, db: AsyncSession):
        return await self.repository.get_all_subjects(db)

    async def get_sessions(self, db: AsyncSession):
        return await self.repository.get_all_unique_sessions(db)

    async def get_terms(self, db: AsyncSession):
        return await self.repository.get_all_unique_terms(db)

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
        return await self.repository.get_lessons(
            db=db,
            class_template_id=class_template_id,
            subject_template_id=subject_template_id,
            session_id=session_id,
            term_id=term_id,
            week_number=week_number,
        )

    async def delete(
        self,
        db: AsyncSession,
        lesson_id: UUID,
    ):
        lesson = await self.repository.get_by_id(db, lesson_id)

        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        await self.repository.delete(db, lesson_id)

    async def get_class_subjects(
        self,
        db: AsyncSession,
        class_template_id: UUID,
    ):
        return await self.repository.get_subjects_by_class_template(
            db,
            class_template_id,
        )
