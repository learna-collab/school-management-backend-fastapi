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
from app.services.document_reader import DocumentReader


class LessonService:
    def __init__(self):
        self.repository = LessonRepository()
        self.parser = LessonParser()
        self.document_reader = DocumentReader()

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
        """
        Uploads the original lesson document, extracts its text,
        parses the existing ALF structure, and saves the lesson.

        The extracted source text is retained separately for
        AI-powered Learning Centre content generation.
        """

        filename = file.filename or "lesson"

        suffix = Path(filename).suffix.lower()

        if suffix not in {".pdf", ".docx"}:
            raise HTTPException(
                status_code=400,
                detail="Only PDF and DOCX lesson documents are supported.",
            )

        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The uploaded lesson document is empty.",
            )

        temp_path = None

        try:
            # --------------------------------------------------
            # GET SUBJECT INFORMATION
            # --------------------------------------------------

            subject = await db.get(
                SubjectTemplate,
                subject_template_id,
            )

            if not subject:
                raise HTTPException(
                    status_code=404,
                    detail="Subject template not found.",
                )

            subject_name = subject.name.replace(" ", "-")

            # --------------------------------------------------
            # EXTRACT ORIGINAL DOCUMENT TEXT
            # --------------------------------------------------

            try:
                source_text = self.document_reader.read_bytes(
                    file_bytes=contents,
                    suffix=suffix,
                )

            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=str(exc),
                ) from exc

            # --------------------------------------------------
            # SAVE TEMPORARILY FOR EXISTING LESSON PARSER
            # --------------------------------------------------

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp:
                temp.write(contents)
                temp_path = temp.name

            # --------------------------------------------------
            # EXISTING LESSON PARSING
            # --------------------------------------------------

            parsed = await self.parser.parse(
                file_path=temp_path,
                week_number=week_number,
            )

            # --------------------------------------------------
            # UPLOAD ORIGINAL DOCUMENT TO CLOUDINARY
            # --------------------------------------------------

            upload_result = await cloudinary_service.upload_bytes(
                contents=contents,
                filename=filename,
                folder="lessons/daily",
                public_id=(
                    f"Week-{week_number}-{subject_name}{suffix}"
                ),
                resource_type="raw",
            )

            file_url = upload_result["url"]

            # --------------------------------------------------
            # CREATE LESSON
            # --------------------------------------------------

            lesson = Lesson(
                created_by=created_by,
                class_template_id=class_template_id,
                subject_template_id=subject_template_id,
                session_id=session_id,
                term_id=term_id,
                week_number=parsed.week_number,
                title=parsed.title or "Untitled Lesson",
                topic=parsed.topic or parsed.title or "Untitled Lesson",
                objectives=(
                    parsed.objectives
                    or "Objectives not extracted from document."
                ),
                teacher_notes=parsed.teacher_notes,
                file_url=file_url,

                # New field for AI Learning Centre.
                # Retains the actual extracted source material.
                source_text=source_text,
            )

            lesson = await self.repository.create(
                db,
                lesson,
            )

            # --------------------------------------------------
            # CREATE EXISTING ALF RECORD
            # --------------------------------------------------

            alf = LessonALF(
                lesson_id=lesson.id,
                independent_reading=(
                    parsed.alf.independent_reading
                ),
                mini_lesson=parsed.alf.mini_lesson,
                case_study=parsed.alf.case_study,
                project_based_learning=(
                    parsed.alf.project_based_learning
                ),
                evaluation=parsed.alf.evaluation,
            )

            await self.repository.create_alf(
                db,
                alf,
            )

            await db.commit()

            # --------------------------------------------------
            # RETURN CREATED LESSON
            # --------------------------------------------------

            lesson = await self.repository.get_by_id(
                db,
                lesson.id,
            )

            return lesson

        except HTTPException:
            raise

        except Exception:
            await db.rollback()
            raise

        finally:
            # --------------------------------------------------
            # CLEAN TEMPORARY FILE
            # --------------------------------------------------

            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

            await file.close()

    # ==========================================================
    # GET LESSON
    # ==========================================================

    async def get_lesson(
        self,
        db: AsyncSession,
        lesson_id: UUID,
    ):
        return await self.repository.get_by_id(
            db,
            lesson_id,
        )

    # ==========================================================
    # CLASSES
    # ==========================================================

    async def get_classes(self, db: AsyncSession):
        return await self.repository.get_all_classes(db)

    # ==========================================================
    # SUBJECTS
    # ==========================================================

    async def get_subjects(self, db: AsyncSession):
        return await self.repository.get_all_subjects(db)

    # ==========================================================
    # SESSIONS
    # ==========================================================

    async def get_sessions(self, db: AsyncSession):
        return await self.repository.get_all_unique_sessions(db)

    # ==========================================================
    # TERMS
    # ==========================================================

    async def get_terms(self, db: AsyncSession):
        return await self.repository.get_all_unique_terms(db)

    # ==========================================================
    # GET LESSONS
    # ==========================================================

    async def get_lessons(
        self,
        db: AsyncSession,
        *,
        class_template_id: UUID,
        session_id: UUID,
        term_id: UUID,
        week_number: int | None = None,
    ):
        return await self.repository.get_lessons(
            db=db,
            class_template_id=class_template_id,
            session_id=session_id,
            term_id=term_id,
            week_number=week_number,
        )

    # ==========================================================
    # DELETE LESSON
    # ==========================================================

    async def delete(
        self,
        db: AsyncSession,
        lesson_id: UUID,
    ):
        lesson = await self.repository.get_by_id(
            db,
            lesson_id,
        )

        if not lesson:
            raise HTTPException(
                status_code=404,
                detail="Lesson not found",
            )

        await self.repository.delete(
            db,
            lesson_id,
        )

        await db.commit()

    # ==========================================================
    # CLASS SUBJECTS
    # ==========================================================

    async def get_class_subjects(
        self,
        db: AsyncSession,
        class_template_id: UUID,
    ):
        return await self.repository.get_subjects_by_class_template(
            db,
            class_template_id,
        )


lesson_service = LessonService()