from sqlalchemy import select

from app.models.school_gallery import SchoolGallery


class SchoolGalleryRepository:
    async def get_school_gallery(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(SchoolGallery)
            .where(
                SchoolGallery.school_id == school_id,
                SchoolGallery.is_visible.is_(True),
            )
            .order_by(
                SchoolGallery.display_order.asc(),
                SchoolGallery.created_at.asc(),
            )
        )

        return result.scalars().all()

    async def get_all_for_admin(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(SchoolGallery)
            .where(SchoolGallery.school_id == school_id)
            .order_by(SchoolGallery.display_order.asc())
        )

        return result.scalars().all()

    async def get_by_id(
        self,
        db,
        image_id,
    ):
        result = await db.execute(
            select(SchoolGallery).where(SchoolGallery.id == image_id)
        )

        return result.scalar_one_or_none()

    async def clear_cover(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(SchoolGallery).where(
                SchoolGallery.school_id == school_id,
                SchoolGallery.is_cover.is_(True),
            )
        )

        for image in result.scalars():
            image.is_cover = False

    async def save(
        self,
        db,
        image,
    ):
        db.add(image)
        await db.commit()
        await db.refresh(image)
        return image

    async def delete(
        self,
        db,
        image,
    ):
        await db.delete(image)
        await db.commit()
