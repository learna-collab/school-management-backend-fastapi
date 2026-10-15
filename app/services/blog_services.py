import logging
from urllib.parse import urlparse

import cloudinary.uploader
import slugify
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_attachment import BlogAttachment
from app.models.blog_post import BlogPost
from app.repositories.blog_attachment_repository import (
    blog_attachment_repo,
)
from app.repositories.blog_repository import BlogRepository
from app.utils.reading_time import calculate_reading_time

logger = logging.getLogger(__name__)

ATTACHMENT_FOLDER = "lerna/blog-attachments"
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024


class BlogService:
    def __init__(self):
        self.repo = BlogRepository()
        self.attachment_repo = blog_attachment_repo

    # =========================
    # ATTACHMENT HELPERS
    # =========================
    def _validate_attachment(self, item: dict) -> None:
        filename = item.get("filename", "").strip()
        url = item.get("url", "")
        public_id = item.get("public_id", "")
        file_size = item.get("file_size", 0)

        if not filename or len(filename) > 255:
            raise HTTPException(
                status_code=400,
                detail="Invalid attachment filename.",
            )

        parsed_url = urlparse(url)

        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname
            not in {
                "res.cloudinary.com",
            }
            or not parsed_url.path
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid attachment URL.",
            )

        if (
            not public_id
            or not public_id.startswith(f"{ATTACHMENT_FOLDER}/")
            or len(public_id) > 500
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid attachment storage reference.",
            )

        if not isinstance(file_size, int) or not (
            0 <= file_size <= MAX_ATTACHMENT_SIZE
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid attachment file size.",
            )

    async def _add_attachments(
        self,
        db: AsyncSession,
        blog_id: str,
        attachments: list[dict],
    ) -> None:
        seen_public_ids: set[str] = set()

        for item in attachments:
            self._validate_attachment(item)

            public_id = item["public_id"]

            if public_id in seen_public_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Duplicate attachment detected.",
                )

            seen_public_ids.add(public_id)

            attachment = BlogAttachment(
                blog_id=blog_id,
                filename=item["filename"].strip(),
                url=item["url"],
                public_id=public_id,
                content_type=item.get("content_type"),
                file_size=item["file_size"],
            )

            await self.attachment_repo.create(db, attachment)

    async def _replace_attachments(
        self,
        db: AsyncSession,
        blog_id: str,
        attachments: list[dict],
    ) -> list[str]:
        """
        Reconcile the requested attachment list with the existing
        records. Returns Cloudinary public IDs to delete only after
        the database transaction commits.
        """
        existing = await self.attachment_repo.get_by_blog(
            db,
            blog_id,
        )

        existing_by_public_id = {item.public_id: item for item in existing}

        requested_ids: set[str] = set()
        delete_after_commit: list[str] = []

        for item in attachments:
            self._validate_attachment(item)

            public_id = item["public_id"]

            if public_id in requested_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Duplicate attachment detected.",
                )

            requested_ids.add(public_id)

        # Keep matching records; create records for new uploads.
        for item in attachments:
            public_id = item["public_id"]

            if public_id in existing_by_public_id:
                continue

            await self.attachment_repo.create(
                db,
                BlogAttachment(
                    blog_id=blog_id,
                    filename=item["filename"].strip(),
                    url=item["url"],
                    public_id=public_id,
                    content_type=item.get("content_type"),
                    file_size=item["file_size"],
                ),
            )

        # Remove omitted records from the database transaction.
        for item in existing:
            if item.public_id not in requested_ids:
                delete_after_commit.append(item.public_id)
                await self.attachment_repo.delete(db, item)

        return delete_after_commit

    async def _delete_cloudinary_files(
        self,
        public_ids: list[str],
    ) -> None:
        for public_id in public_ids:
            try:
                cloudinary.uploader.destroy(
                    public_id,
                    resource_type="raw",
                )
            except Exception:
                logger.exception(
                    "Failed to delete Cloudinary attachment %s",
                    public_id,
                )

    # =========================
    # CREATE BLOG
    # =========================
    async def create_blog(
        self,
        db: AsyncSession,
        data: dict,
        admin_id: str,
    ):
        attachments = data.get("attachments") or []

        blog = BlogPost(
            title=data["title"],
            slug=slugify.slugify(
                data["title"],
                lowercase=True,
                separator="-",
            ),
            excerpt=data["excerpt"],
            content=data["content"],
            cover_image=data.get("coverImage"),
            cover_image_id=data.get("coverImageId"),
            published=data.get("published", False),
            featured=data.get("featured", False),
            seo_title=data.get("seoTitle"),
            seo_description=data.get("seoDescription"),
            reading_time=calculate_reading_time(data["content"]),
            author_id=admin_id,
        )

        # Validate before creating the post.
        for item in attachments:
            self._validate_attachment(item)

        # Preserve the existing repository's create behavior.
        blog = await self.repo.create(db, blog)

        try:
            await self._add_attachments(
                db,
                str(blog.id),
                attachments,
            )
            await db.commit()
            await db.refresh(blog)
        except Exception:
            await db.rollback()
            raise

        return blog

    # =========================
    # GET ALL
    # =========================
    async def get_blogs(self, db: AsyncSession):
        return await self.repo.get_all(db)

    # =========================
    # GET FEATURED
    # =========================
    async def get_featured_blogs(self, db: AsyncSession):
        return await self.repo.get_featured(db)

    # =========================
    # GET ONE
    # =========================
    async def get_blog(self, db, blog_id: str):
        return await self.repo.get_by_id(db, blog_id)

    # =========================
    # UPDATE BLOG
    # =========================
    async def update_blog(
        self,
        db: AsyncSession,
        blog,
        data: dict,
    ):
        if "title" in data:
            blog.title = data["title"]
            blog.slug = slugify.slugify(
                data["title"],
                lowercase=True,
                separator="-",
            )

        if "excerpt" in data:
            blog.excerpt = data["excerpt"]

        if "content" in data:
            blog.content = data["content"]
            blog.reading_time = calculate_reading_time(data["content"])

        if "coverImage" in data:
            blog.cover_image = data.get("coverImage")

        if "coverImageId" in data:
            blog.cover_image_id = data.get("coverImageId")

        if "published" in data:
            blog.published = data["published"]

        if "featured" in data:
            blog.featured = data["featured"]

        if "seoTitle" in data:
            blog.seo_title = data.get("seoTitle")

        if "seoDescription" in data:
            blog.seo_description = data.get("seoDescription")

        delete_after_commit: list[str] = []

        try:
            if "attachments" in data and data["attachments"] is not None:
                delete_after_commit = await self._replace_attachments(
                    db,
                    str(blog.id),
                    data["attachments"],
                )

            await self.repo.update(db, blog)

            # The existing repository commits the blog update.
            # Commit any pending attachment changes as well.
            await db.commit()
            await db.refresh(blog)

        except Exception:
            await db.rollback()
            raise

        # Cloudinary cleanup happens only after database changes
        # have succeeded.
        await self._delete_cloudinary_files(delete_after_commit)

        return blog

    # =========================
    # DELETE BLOG
    # =========================
    async def delete_blog(self, db, blog):
        attachments = await self.attachment_repo.get_by_blog(
            db,
            str(blog.id),
        )

        attachment_public_ids = [item.public_id for item in attachments]

        if blog.cover_image_id:
            try:
                cloudinary.uploader.destroy(
                    blog.cover_image_id,
                    resource_type="image",
                )
            except Exception:
                logger.exception("Failed to delete blog cover image.")

        await self.repo.delete(db, blog)
        await db.commit()

        # Delete document files after the post deletion succeeds.
        await self._delete_cloudinary_files(attachment_public_ids)
