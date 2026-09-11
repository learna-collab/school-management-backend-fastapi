import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class DigitalProduct(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_digital_products"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    file_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    file_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    access_type: Mapped[str] = mapped_column(
        String(50),
        default="DOWNLOAD",
        nullable=False,
    )

    instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    listing = relationship(
        "MarketplaceListing",
        back_populates="digital",
    )
