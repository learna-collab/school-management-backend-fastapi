from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.school_gallery import GalleryCategory


class SchoolGalleryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    image_url: str
    caption: str | None
    category: GalleryCategory
    display_order: int
    is_cover: bool
    is_visible: bool


class SchoolGalleryUpdate(BaseModel):
    caption: str | None = None
    category: GalleryCategory | None = None
    display_order: int | None = None
    is_cover: bool | None = None
    is_visible: bool | None = None
