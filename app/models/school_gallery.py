import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.school import School


class GalleryCategory(str, Enum):
    CAMPUS = "CAMPUS"
    CLASSROOM = "CLASSROOM"
    LABORATORY = "LABORATORY"
    LIBRARY = "LIBRARY"
    SPORTS = "SPORTS"
    EVENT = "EVENT"
    STAFF = "STAFF"
    OTHER = "OTHER"


class SchoolGallery(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "school_gallery"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    caption: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    category: Mapped[GalleryCategory] = mapped_column(
        default=GalleryCategory.OTHER,
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_cover: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_visible: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    public_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    school: Mapped["School"] = relationship(
        "School",
        back_populates="gallery",
    )
