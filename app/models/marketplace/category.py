from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class MarketplaceCategory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_categories"

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
    )

    slug: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    listings = relationship(
        "MarketplaceListing",
        back_populates="category",
    )
