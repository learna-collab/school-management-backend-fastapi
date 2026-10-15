from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blog_post import BlogPost


class BlogRepository:
    async def create(
        self,
        db: AsyncSession,
        blog: BlogPost,
    ) -> BlogPost:
        db.add(blog)
        await db.flush()
        await db.refresh(blog)
        return blog

    async def get_all(
        self,
        db: AsyncSession,
    ) -> list[BlogPost]:
        result = await db.execute(select(BlogPost).order_by(BlogPost.created_at.desc()))
        return list(result.scalars().all())

    async def get_featured(
        self,
        db: AsyncSession,
    ) -> list[BlogPost]:
        result = await db.execute(
            select(BlogPost)
            .where(
                BlogPost.featured.is_(True),
                BlogPost.published.is_(True),
            )
            .order_by(BlogPost.created_at.desc())
            .limit(3)
        )
        return list(result.scalars().all())

    async def get_by_id(
        self,
        db: AsyncSession,
        blog_id: str,
    ) -> BlogPost | None:
        result = await db.execute(
            select(BlogPost)
            .options(selectinload(BlogPost.attachments))
            .where(BlogPost.id == blog_id)
        )

        return result.scalar_one_or_none()

    async def delete(
        self,
        db: AsyncSession,
        blog: BlogPost,
    ) -> None:
        await db.delete(blog)
        await db.flush()

    async def update(
        self,
        db: AsyncSession,
        blog: BlogPost,
    ) -> BlogPost:
        await db.flush()
        await db.refresh(blog)
        return blog


blog_repo = BlogRepository()
