# app/models/blog_post.py

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class BlogPost(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "blog_posts"

    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    excerpt: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)

    cover_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cover_image_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False)

    seo_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    reading_time: Mapped[int | None] = mapped_column(Integer, nullable=True)

    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    author = relationship("User")
    attachments = relationship(
        "BlogAttachment",
        back_populates="blog",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
