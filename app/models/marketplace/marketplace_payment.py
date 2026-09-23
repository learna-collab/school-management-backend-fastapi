import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class MarketplacePayment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_payments"

    checkout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "marketplace_checkouts.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    access_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    authorization_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    paid_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reference: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    paystack_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    authorization_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(
            PaymentStatus,
            name="payment_status",
        ),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )

    checkout = relationship(
        "MarketplaceCheckout",
        back_populates="payment",
    )


class MarketplaceWallet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_wallets"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "marketplace_vendors.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    available_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    pending_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    vendor = relationship(
        "Vendor",
    )
