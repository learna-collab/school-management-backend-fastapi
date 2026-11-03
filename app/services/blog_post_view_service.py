from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_post import BlogPost
from app.repositories.blog_post_view_repository import (
    blog_post_view_repository,
)


class BlogPostViewService:
    def __init__(self):
        self.repo = blog_post_view_repository

    async def record_view(
        self,
        db: AsyncSession,
        blog_id: str,
        visitor_id: str,
    ) -> dict:
        blog_result = await db.execute(
            select(BlogPost.id).where(BlogPost.id == blog_id)
        )

        if blog_result.scalar_one_or_none() is None:
            return {"found": False}

        today = datetime.now(ZoneInfo("Africa/Lagos")).date()

        await self.repo.record_daily_view(
            db=db,
            blog_id=blog_id,
            visitor_id=visitor_id,
            view_date=today,
        )

        await db.commit()

        unique_visitors = await self.repo.get_unique_visitors(
            db=db,
            blog_id=blog_id,
        )

        daily_unique_views = await self.repo.get_daily_unique_views(
            db=db,
            blog_id=blog_id,
        )

        return {
            "found": True,
            "unique_visitors": unique_visitors,
            "daily_unique_views": daily_unique_views,
        }


blog_post_view_service = BlogPostViewService()
