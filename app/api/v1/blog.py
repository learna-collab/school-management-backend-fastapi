from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import RequireSuperAdmin
from app.db.database import get_db
from app.schemas.blog import BlogCreate, BlogUpdate  # 👈 ADD THIS
from app.services.blog_services import BlogService

router = APIRouter(tags=["Blogs"], prefix="/blogs")
service = BlogService()


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
