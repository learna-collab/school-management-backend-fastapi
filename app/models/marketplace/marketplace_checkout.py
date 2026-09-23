import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class CheckoutStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MarketplaceCheckout(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "marketplace_checkouts"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    checkout_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="NGN",
    )

    status: Mapped[CheckoutStatus] = mapped_column(
        SAEnum(
            CheckoutStatus,
            name="checkout_status",
        ),
        nullable=False,
        default=CheckoutStatus.PENDING,
        index=True,
    )

    stock_restored: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    customer = relationship("User")

    orders = relationship(
        "MarketplaceOrder",
        back_populates="checkout",
    )

    payment = relationship(
        "MarketplacePayment",
        back_populates="checkout",
        uselist=False,
    )
