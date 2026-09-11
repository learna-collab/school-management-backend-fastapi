import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ListingImage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_listing_images"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    image_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    listing = relationship(
        "MarketplaceListing",
        back_populates="images",
    )
