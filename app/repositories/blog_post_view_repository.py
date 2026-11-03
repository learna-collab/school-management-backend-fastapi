from datetime import date

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_post_view import BlogPostView


class BlogPostViewRepository:
    async def record_daily_view(
        self,
        db: AsyncSession,
        blog_id: str,
        visitor_id: str,
        view_date: date,
    ) -> None:
        statement = (
            insert(BlogPostView)
            .values(
                blog_id=blog_id,
                visitor_id=visitor_id,
                view_date=view_date,
            )
            .on_conflict_do_nothing(constraint="uq_blog_view_visitor_per_day")
        )

        await db.execute(statement)

    async def get_unique_visitors(
        self,
        db: AsyncSession,
        blog_id: str,
    ) -> int:
        statement = select(func.count(func.distinct(BlogPostView.visitor_id))).where(
            BlogPostView.blog_id == blog_id
        )

        result = await db.execute(statement)
        return result.scalar_one() or 0

    async def get_daily_unique_views(
        self,
        db: AsyncSession,
        blog_id: str,
    ) -> int:
        statement = select(func.count(BlogPostView.id)).where(
            BlogPostView.blog_id == blog_id
        )

        result = await db.execute(statement)
        return result.scalar_one() or 0


blog_post_view_repository = BlogPostViewRepository()
