import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class PhysicalProduct(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_physical_products"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    sku: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )

    dimensions: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    listing = relationship(
        "MarketplaceListing",
        back_populates="physical",
    )
