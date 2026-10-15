from typing import Optional

from pydantic import BaseModel, Field


class BlogAttachmentInput(BaseModel):
    """
    Represents an attachment that has already been uploaded
    to Cloudinary and is being associated with a blog post.
    """

    filename: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1)
    public_id: str = Field(min_length=1, max_length=500)
    content_type: Optional[str] = Field(
        default=None,
        max_length=150,
    )
    file_size: int = Field(ge=0)


class BlogCreate(BaseModel):
    title: str
    excerpt: str
    content: str

    coverImage: Optional[str] = None
    coverImageId: Optional[str] = None

    # All attachments to associate with this new post.
    attachments: list[BlogAttachmentInput] = Field(default_factory=list)

    published: bool = False
    featured: bool = False

    seoTitle: Optional[str] = None
    seoDescription: Optional[str] = None


class BlogUpdate(BaseModel):
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None

    coverImage: Optional[str] = None
    coverImageId: Optional[str] = None

    # When omitted, existing attachments remain unchanged.
    # When supplied, this becomes the complete desired list.
    attachments: Optional[list[BlogAttachmentInput]] = None

    published: Optional[bool] = None
    featured: Optional[bool] = None

    seoTitle: Optional[str] = None
    seoDescription: Optional[str] = None
