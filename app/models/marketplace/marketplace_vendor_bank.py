import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class VendorBankAccount(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "marketplace_vendor_bank_accounts"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_vendors.id"),
    )

    bank_name: Mapped[str] = mapped_column(String(120))
    bank_code: Mapped[str] = mapped_column(String(20))
    account_name: Mapped[str] = mapped_column(String(255))
    account_number: Mapped[str] = mapped_column(String(20))

    recipient_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    vendor = relationship("Vendor")
