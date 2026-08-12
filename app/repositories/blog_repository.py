from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_post import BlogPost


class BlogRepository:
    async def create(self, db: AsyncSession, blog: BlogPost):
        db.add(blog)
        await db.commit()
        await db.refresh(blog)
        return blog

    async def get_all(self, db: AsyncSession):
        result = await db.execute(select(BlogPost).order_by(BlogPost.created_at.desc()))
        return result.scalars().all()

    async def get_featured(self, db):
        result = await db.execute(
            select(BlogPost)
            .where(
                BlogPost.featured == True,
                BlogPost.published == True,
            )
            .order_by(BlogPost.created_at.desc())
            .limit(3)
        )
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, blog_id: str):
        result = await db.execute(select(BlogPost).where(BlogPost.id == blog_id))
        return result.scalar_one_or_none()

    async def delete(self, db: AsyncSession, blog: BlogPost):
        await db.delete(blog)
        await db.commit()

    async def update(self, db: AsyncSession, blog: BlogPost):
        await db.commit()
        await db.refresh(blog)
        return blog
