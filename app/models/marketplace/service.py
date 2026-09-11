import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class MarketplaceService(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_services"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    pricing_model: Mapped[str] = mapped_column(
        String(50),
        default="FIXED",
        nullable=False,
    )

    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    service_area: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    availability: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    listing = relationship(
        "MarketplaceListing",
        back_populates="service",
    )
