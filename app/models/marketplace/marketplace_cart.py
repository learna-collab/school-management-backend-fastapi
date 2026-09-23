import uuid

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class MarketplaceCart(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_carts"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    customer = relationship("User")

    items = relationship(
        "MarketplaceCartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )


class MarketplaceCartItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_cart_items"

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "marketplace_carts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "marketplace_listings.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    cart = relationship(
        "MarketplaceCart",
        back_populates="items",
    )

    listing = relationship(
        "MarketplaceListing",
    )

    __table_args__ = (
        UniqueConstraint(
            "cart_id",
            "listing_id",
            name="uq_marketplace_cart_listing",
        ),
    )
