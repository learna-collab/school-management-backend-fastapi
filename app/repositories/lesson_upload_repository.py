from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lesson import Lesson
from app.models.lesson_upload import LessonUpload


class LessonUploadRepository:
    async def create(
        self,
        db: AsyncSession,
        upload: LessonUpload,
    ) -> LessonUpload:
        db.add(upload)
        await db.flush()
        await db.refresh(upload)
        return upload

    async def update_total_lessons(
        self,
        db: AsyncSession,
        upload_id: UUID,
        total: int,
    ) -> LessonUpload:
        upload = await self.get_by_id(db, upload_id)

        upload.total_lessons = total

        await db.flush()
        await db.refresh(upload)

        return upload

    async def get_by_id(
        self,
        db: AsyncSession,
        upload_id: UUID,
    ) -> LessonUpload | None:
        result = await db.execute(
            select(LessonUpload)
            .options(
                selectinload(LessonUpload.lessons),
            )
            .where(LessonUpload.id == upload_id)
        )

        return result.scalar_one_or_none()

    async def get_upload_history(
        self,
        db: AsyncSession,
        session_id: UUID,
        term_id: UUID,
    ):
        result = await db.execute(
            select(LessonUpload)
            .where(
                LessonUpload.session_id == session_id,
                LessonUpload.term_id == term_id,
            )
            .order_by(LessonUpload.created_at.desc())
        )

        return result.scalars().all()

    async def delete_upload(
        self,
        db: AsyncSession,
        upload_id: UUID,
    ):
        await db.execute(delete(LessonUpload).where(LessonUpload.id == upload_id))

    async def count_uploads(
        self,
        db: AsyncSession,
    ) -> int:
        result = await db.execute(select(func.count()).select_from(LessonUpload))

        return result.scalar_one()
