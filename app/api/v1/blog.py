from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import RequireSuperAdmin
from app.db.database import get_db
from app.models.blog_attachment import BlogAttachment
from app.schemas.blog import BlogCreate, BlogUpdate  # 👈 ADD THIS
from app.services.blog_attachment_service import blog_attachment_upload_service
from app.services.blog_services import BlogService

router = APIRouter(tags=["Blogs"], prefix="/blogs")
service = BlogService()


@router.get("/{blog_id}/attachments/{attachment_id}/preview")
async def preview_blog_attachment(
    blog_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BlogAttachment).where(
            BlogAttachment.id == attachment_id,
            BlogAttachment.blog_id == blog_id,
        )
    )

    attachment = result.scalar_one_or_none()

    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail="Attachment not found",
        )

    filename = attachment.filename.replace("\r", "").replace("\n", "")

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=415,
            detail="Only PDF files can be previewed.",
        )

    try:
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
        ) as client:
            upstream = await client.get(attachment.url)
            upstream.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to load PDF preview.",
        ) from exc

    return Response(
        content=upstream.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"inline; filename*=UTF-8''{quote(filename, safe='')}"
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get("/{blog_id}/attachments/{attachment_id}/download")
async def download_blog_attachment(
    blog_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BlogAttachment).where(
            BlogAttachment.id == attachment_id,
            BlogAttachment.blog_id == blog_id,
        )
    )
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(
            status_code=404,
            detail="Attachment not found",
        )

    try:
        async with httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
        ) as client:
            file_response = await client.get(attachment.url)
            file_response.raise_for_status()

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve the attachment",
        )

    filename = attachment.filename.replace("\r", "").replace("\n", "")
    encoded_filename = quote(filename, safe="")

    return Response(
        content=file_response.content,
        media_type=attachment.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": (f"attachment; filename*=UTF-8''{encoded_filename}"),
            "Content-Length": str(len(file_response.content)),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/attachments/upload")
async def upload_blog_attachment(
    admin: RequireSuperAdmin,
    file: UploadFile = File(...),
):
    return await blog_attachment_upload_service.upload(file)


# =========================
# CREATE BLOG
# =========================
@router.post("/")
async def create_blog(
    data: BlogCreate,
    admin: RequireSuperAdmin,
    db: AsyncSession = Depends(get_db),
):
    return await service.create_blog(db, data.model_dump(), admin.id)


# =========================
# GET ALL BLOGS
# =========================
@router.get("/")
async def get_blogs(db: AsyncSession = Depends(get_db)):
    return await service.get_blogs(db)


# =========================
# GET FEATURED BLOGS (IMPORTANT)
# =========================
@router.get("/featured")
async def get_featured_blogs(db: AsyncSession = Depends(get_db)):
    return await service.get_featured_blogs(db)


# =========================
# GET SINGLE BLOG
# =========================
@router.get("/{blog_id}")
async def get_blog(blog_id: str, db: AsyncSession = Depends(get_db)):
    blog = await service.get_blog(db, blog_id)
    if not blog:
        raise HTTPException(404, "Not found")
    return blog


# =========================
# UPDATE BLOG
# =========================
@router.patch("/{blog_id}")
async def update_blog(
    blog_id: str,
    data: BlogUpdate,
    _: RequireSuperAdmin,
    db: AsyncSession = Depends(get_db),
):
    blog = await service.get_blog(db, blog_id)
    if not blog:
        raise HTTPException(404, "Not found")

    return await service.update_blog(db, blog, data.model_dump(exclude_unset=True))


# =========================
# DELETE BLOG
# =========================
@router.delete("/{blog_id}")
async def delete_blog(
    blog_id: str,
    _: RequireSuperAdmin,
    db: AsyncSession = Depends(get_db),
):
    blog = await service.get_blog(db, blog_id)
    if not blog:
        raise HTTPException(404, "Not found")

    await service.delete_blog(db, blog)
    return {"success": True}
