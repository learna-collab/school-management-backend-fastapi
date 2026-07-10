from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import mapped_column, relationship

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class UserCredential(
    Base,
    UUIDMixin,
    TenantMixin,
    TimestampMixin,
):
    __tablename__ = "user_credentials"

    user_id = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    password = mapped_column(
        String(255),
        nullable=False,
    )
    username = mapped_column(
        String(255),
        nullable=True,
    )

    user = relationship(
        "User",
        back_populates="credential",
    )
