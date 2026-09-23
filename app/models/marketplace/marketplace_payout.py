import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class PayoutStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class MarketplacePayout(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "marketplace_payouts"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "marketplace_vendors.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "marketplace_orders.id",
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

    bank_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    account_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    recipient_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    reference: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    transfer_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    status: Mapped[PayoutStatus] = mapped_column(
        SAEnum(PayoutStatus),
        default=PayoutStatus.PENDING,
        nullable=False,
        index=True,
    )

    vendor = relationship(
        "Vendor",
        back_populates="payouts",
    )

    order = relationship(
        "MarketplaceOrder",
    )
