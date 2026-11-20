import logging
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.lesson_learning_content import LessonLearningContent
from app.repositories.learning_content_repository import (
    LearningContentRepository,
)
from app.schemas.learning_centre import LessonLearningDocument
from app.services.learning_content_generator import (
    LearningContentGenerationError,
    LearningContentGenerator,
)

logger = logging.getLogger(__name__)


class LearningContentService:
    def __init__(self):
        self.repository = LearningContentRepository()

    # ==========================================================
    # AI GENERATOR CONFIGURATION
    # ==========================================================

    def _get_generator(self) -> LearningContentGenerator:
        api_key = settings.openai_api_key

        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="AI content generation is not configured.",
            )

        return LearningContentGenerator(
            api_key=api_key,
            model=settings.openai_model,
        )

    # ==========================================================
    # GENERATE CONTENT
    # ==========================================================

    async def generate_for_lesson(
        self,
        *,
        db: AsyncSession,
        lesson_id: UUID,
        generated_by: UUID,
    ) -> LessonLearningContent:
        lesson = await self.repository.get_lesson(
            db,
            lesson_id,
        )

        if not lesson:
            raise HTTPException(
                status_code=404,
                detail="Lesson not found.",
            )

        generator = self._get_generator()

        try:
            # --------------------------------------------------
            # EXTRACT ORIGINAL LESSON NOTES
            # --------------------------------------------------

            had_saved_source_text = bool(
                getattr(lesson, "source_text", None)
                and lesson.source_text.strip()
            )

            source_text = await generator.get_source_text(lesson)

            if not source_text or not source_text.strip():
                raise LearningContentGenerationError(
                    "No readable lesson content was found. "
                    "Upload a valid PDF or DOCX lesson note."
                )

            if not had_saved_source_text:
                # Cache extracted text independently so an OpenAI failure
                # does not force another Cloudinary download on the next run.
                lesson.source_text = source_text
                await db.flush()
                await db.commit()
                lesson = await self.repository.get_lesson(db, lesson_id)

            # --------------------------------------------------
            # GET CLASS AND SUBJECT INFORMATION
            # --------------------------------------------------

            class_name = (
                getattr(
                    lesson.class_template,
                    "name",
                    "General class",
                )
                if lesson.class_template
                else "General class"
            )

            subject_name = (
                getattr(
                    lesson.subject_template,
                    "name",
                    "General subject",
                )
                if lesson.subject_template
                else "General subject"
            )

            # --------------------------------------------------
            # GENERATE STRUCTURED LEARNING CONTENT
            # --------------------------------------------------

            generated_content = await generator.generate(
                source_text=source_text,
                title=lesson.title,
                topic=lesson.topic,
                objectives=lesson.objectives,
                class_name=class_name,
                subject_name=subject_name,
            )

            # Validate generated data against your actual schema.

            content_data = generated_content

            # --------------------------------------------------
            # GENERATE NEXT VERSION NUMBER
            # --------------------------------------------------

            version = await self.repository.get_next_version(
                db,
                lesson_id,
            )

            warnings = content_data.get(
                "generation_warnings",
                [],
            )

            # --------------------------------------------------
            # CREATE NEW LEARNING CONTENT VERSION
            # --------------------------------------------------

            learning_content = LessonLearningContent(
                lesson_id=lesson.id,
                school_id=None,
                version=version,
                status="GENERATED",
                content=content_data,
                generation_notes="\n".join(warnings) or None,
                generated_by=generated_by,
            )

            await self.repository.create_content(
                db,
                learning_content,
            )

            # Commits both the new content and extracted
            # Lesson.source_text, if it was populated.
            await db.commit()

            await db.refresh(learning_content)

            return learning_content

        except LearningContentGenerationError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

        except IntegrityError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Another content version may have been generated "
                    "for this lesson simultaneously. Please try again."
                ),
            ) from exc

        except HTTPException:
            await db.rollback()
            raise

        except Exception as exc:
            await db.rollback()

            logger.exception(
                "Unexpected error while generating learning content. "
                "Lesson ID: %s. Error type: %s. Error: %s",
                lesson_id,
                type(exc).__name__,
                str(exc),
            )

            raise HTTPException(
                status_code=500,
                detail="An error occurred while generating lesson content.",
            ) from exc
        finally:
            await generator.close()

    # ==========================================================
    # GET ALL CONTENT VERSIONS FOR A LESSON
    # ==========================================================

    async def get_lesson_versions(
        self,
        db: AsyncSession,
        lesson_id: UUID,
    ):
        lesson = await self.repository.get_lesson(
            db,
            lesson_id,
        )

        if not lesson:
            raise HTTPException(
                status_code=404,
                detail="Lesson not found.",
            )

        return await self.repository.get_lesson_versions(
            db,
            lesson_id,
        )

    # ==========================================================
    # GET ONE CONTENT VERSION
    # ==========================================================

    async def get_content(
        self,
        db: AsyncSession,
        content_id: UUID,
    ):
        content = await self.repository.get_content(
            db,
            content_id,
        )

        if not content:
            raise HTTPException(
                status_code=404,
                detail="Learning content not found.",
            )

        return content

    # ==========================================================
    # REVIEW / EDIT GENERATED CONTENT
    # ==========================================================

    async def review_content(
        self,
        *,
        db: AsyncSession,
        content_id: UUID,
        reviewed_by: UUID,
        content_data: LessonLearningDocument,
        review_notes: str | None = None,
    ) -> LessonLearningContent:
        content = await self.repository.get_content(
            db,
            content_id,
        )

        if not content:
            raise HTTPException(
                status_code=404,
                detail="Learning content not found.",
            )

        if content.status not in {"GENERATED", "REVIEWED"}:
            raise HTTPException(
                status_code=409,
                detail=("Only generated or previously reviewed content can be edited."),
            )

        try:
            # --------------------------------------------------
            # SAVE REVIEWED CONTENT
            # --------------------------------------------------

            content.content = content_data.model_dump(mode="json")

            content.status = "REVIEWED"
            content.reviewed_by = reviewed_by
            content.review_notes = review_notes

            await self.repository.update_content(
                db,
                content,
            )

            await db.commit()
            await db.refresh(content)

            return content

        except Exception:
            await db.rollback()
            raise

    # ==========================================================
    # PUBLISH REVIEWED CONTENT
    # ==========================================================

    async def publish_content(
        self,
        *,
        db: AsyncSession,
        content_id: UUID,
        published_by: UUID,
    ) -> LessonLearningContent:
        content = await self.repository.get_content(
            db,
            content_id,
        )

        if not content:
            raise HTTPException(
                status_code=404,
                detail="Learning content not found.",
            )

        if content.status != "REVIEWED":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only reviewed learning content can be published. "
                    "Review the content before publishing."
                ),
            )

        try:
            content.status = "PUBLISHED"
            content.published_by = published_by
            content.published_at = datetime.now(timezone.utc)

            await self.repository.update_content(
                db,
                content,
            )

            await db.commit()
            await db.refresh(content)

            return content

        except Exception:
            await db.rollback()
            raise
