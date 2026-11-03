from datetime import date

from sqlalchemy import (
    Date,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class BlogPostView(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "blog_post_views"

    __table_args__ = (
        UniqueConstraint(
            "blog_id",
            "visitor_id",
            "view_date",
            name="uq_blog_view_visitor_per_day",
        ),
    )

    blog_id: Mapped[str] = mapped_column(
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    visitor_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    view_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
