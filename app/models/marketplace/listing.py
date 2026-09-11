import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ListingType(str, Enum):
    PHYSICAL = "PHYSICAL"
    SERVICE = "SERVICE"
    DIGITAL = "DIGITAL"


class ListingStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class MarketplaceListing(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_listings"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    listing_type: Mapped[ListingType] = mapped_column(
        SAEnum(ListingType, name="listing_type"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="NGN",
        nullable=False,
    )

    status: Mapped[ListingStatus] = mapped_column(
        SAEnum(ListingStatus, name="listing_status"),
        default=ListingStatus.DRAFT,
        nullable=False,
        index=True,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    vendor = relationship("Vendor", back_populates="listings")
    category = relationship(
        "MarketplaceCategory",
        back_populates="listings",
    )

    images = relationship(
        "ListingImage",
        back_populates="listing",
        cascade="all, delete-orphan",
    )

    physical = relationship(
        "PhysicalProduct",
        back_populates="listing",
        uselist=False,
        cascade="all, delete-orphan",
    )

    service = relationship(
        "MarketplaceService",
        back_populates="listing",
        uselist=False,
        cascade="all, delete-orphan",
    )

    digital = relationship(
        "DigitalProduct",
        back_populates="listing",
        uselist=False,
        cascade="all, delete-orphan",
    )
