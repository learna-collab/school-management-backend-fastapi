import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID_HELD = "PAID_HELD"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class MarketplaceOrder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_orders"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "marketplace_vendors.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    checkout_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "marketplace_checkouts.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    vendor_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus),
        default=OrderStatus.PENDING,
        nullable=False,
    )

    delivery_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    released: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    customer = relationship("User")

    vendor = relationship(
        "Vendor",
        back_populates="orders",
    )

    checkout = relationship(
        "MarketplaceCheckout",
        back_populates="orders",
    )

    items = relationship(
        "MarketplaceOrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
