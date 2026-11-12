from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lesson import Lesson
from app.models.lesson_learning_content import LessonLearningContent
from app.models.student_learning_progress import StudentLearningProgress


class LearningContentRepository:
    # ==========================================================
    # LESSON
    # ==========================================================

    async def get_lesson(
        self,
        db: AsyncSession,
        lesson_id: UUID,
    ) -> Lesson | None:
        result = await db.execute(
            select(Lesson)
            .options(
                selectinload(Lesson.class_template),
                selectinload(Lesson.subject_template),
            )
            .where(Lesson.id == lesson_id)
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # CONTENT VERSIONING
    # ==========================================================

    async def get_next_version(
        self,
        db: AsyncSession,
        lesson_id: UUID,
    ) -> int:
        result = await db.execute(
            select(
                func.coalesce(
                    func.max(LessonLearningContent.version),
                    0,
                )
            ).where(
                LessonLearningContent.lesson_id == lesson_id
            )
        )

        return result.scalar_one() + 1

    async def create_content(
        self,
        db: AsyncSession,
        content: LessonLearningContent,
    ) -> LessonLearningContent:
        db.add(content)
        await db.flush()
        await db.refresh(content)

        return content

    async def get_content(
        self,
        db: AsyncSession,
        content_id: UUID,
    ) -> LessonLearningContent | None:
        result = await db.execute(
            select(LessonLearningContent).where(
                LessonLearningContent.id == content_id
            )
        )

        return result.scalar_one_or_none()

    async def get_lesson_versions(
        self,
        db: AsyncSession,
        lesson_id: UUID,
    ) -> list[LessonLearningContent]:
        result = await db.execute(
            select(LessonLearningContent)
            .where(
                LessonLearningContent.lesson_id == lesson_id
            )
            .order_by(
                LessonLearningContent.version.desc()
            )
        )

        return list(result.scalars().all())

    # ==========================================================
    # CONTENT UPDATE
    # ==========================================================

    async def update_content(
        self,
        db: AsyncSession,
        content: LessonLearningContent,
    ) -> LessonLearningContent:
        await db.flush()
        await db.refresh(content)

        return content

    # ==========================================================
    # PUBLISHED STUDENT CONTENT
    # ==========================================================

    async def get_published_content_for_lesson(
        self,
        db: AsyncSession,
        lesson_id: UUID,
        school_id: UUID,
    ) -> LessonLearningContent | None:
        result = await db.execute(
            select(LessonLearningContent)
            .where(
                LessonLearningContent.lesson_id == lesson_id,
                LessonLearningContent.status == "PUBLISHED",
                or_(
                    LessonLearningContent.school_id == school_id,
                    LessonLearningContent.school_id.is_(None),
                ),
            )
            .order_by(
                LessonLearningContent.school_id.is_(None),
                LessonLearningContent.version.desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # STUDENT PROGRESS
    # ==========================================================

    async def get_student_progress(
        self,
        db: AsyncSession,
        learning_content_id: UUID,
        student_id: UUID,
        school_id: UUID,
    ) -> StudentLearningProgress | None:
        result = await db.execute(
            select(StudentLearningProgress).where(
                StudentLearningProgress.learning_content_id
                == learning_content_id,
                StudentLearningProgress.student_id == student_id,
                StudentLearningProgress.school_id == school_id,
            )
        )

        return result.scalar_one_or_none()

    async def create_student_progress(
        self,
        db: AsyncSession,
        progress: StudentLearningProgress,
    ) -> StudentLearningProgress:
        db.add(progress)
        await db.flush()
        await db.refresh(progress)

        return progress

    async def update_student_progress(
        self,
        db: AsyncSession,
        progress: StudentLearningProgress,
    ) -> StudentLearningProgress:
        await db.flush()
        await db.refresh(progress)

        return progress