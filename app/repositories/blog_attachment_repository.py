from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_attachment import BlogAttachment


class BlogAttachmentRepository:
    async def get_by_blog(
        self,
        db: AsyncSession,
        blog_id: str,
    ) -> list[BlogAttachment]:
        result = await db.execute(
            select(BlogAttachment)
            .where(BlogAttachment.blog_id == blog_id)
            .order_by(BlogAttachment.created_at.asc())
        )

        return list(result.scalars().all())

    async def get_by_ids(
        self,
        db: AsyncSession,
        attachment_ids: list[str],
    ) -> list[BlogAttachment]:
        if not attachment_ids:
            return []

        result = await db.execute(
            select(BlogAttachment).where(BlogAttachment.id.in_(attachment_ids))
        )

        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        attachment: BlogAttachment,
    ) -> BlogAttachment:
        db.add(attachment)
        await db.flush()
        return attachment

    async def delete(
        self,
        db: AsyncSession,
        attachment: BlogAttachment,
    ) -> None:
        await db.delete(attachment)
        await db.flush()


blog_attachment_repo = BlogAttachmentRepository()
