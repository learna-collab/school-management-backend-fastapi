import uuid
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class VendorType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    BUSINESS = "BUSINESS"


class VendorStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class Vendor(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_vendors"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    vendor_type: Mapped[VendorType] = mapped_column(
        SAEnum(VendorType, name="vendor_type"),
        nullable=False,
    )

    store_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    business_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    public_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    logo_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[VendorStatus] = mapped_column(
        SAEnum(VendorStatus, name="vendor_status"),
        default=VendorStatus.PENDING,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    user = relationship("User", back_populates="vendor")
    listings = relationship(
        "MarketplaceListing",
        back_populates="vendor",
        cascade="all, delete-orphan",
    )
