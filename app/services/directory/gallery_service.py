from app.models.school_gallery import SchoolGallery
from app.repositories.directory.gallery_repository import (
    SchoolGalleryRepository,
)


class SchoolGalleryService:
    def __init__(self):
        self.repo = SchoolGalleryRepository()

    async def get_gallery(
        self,
        db,
        school_id,
        *,
        admin: bool = False,
    ):
        if admin:
            return await self.repo.get_all_for_admin(
                db,
                school_id,
            )

        return await self.repo.get_school_gallery(
            db,
            school_id,
        )

    async def upload_image(
        self,
        db,
        school_id,
        image_url,
        public_id,
        caption,
        category,
        is_cover,
    ):
        if is_cover:
            await self.repo.clear_cover(
                db,
                school_id,
            )

        existing = await self.repo.get_all_for_admin(
            db,
            school_id,
        )

        next_order = len(existing) + 1

        image = SchoolGallery(
            school_id=school_id,
            image_url=image_url,
            public_id=public_id,
            caption=caption,
            category=category,
            is_cover=is_cover,
            display_order=next_order,
        )

        return await self.repo.save(
            db,
            image,
        )

    async def update_image(
        self,
        db,
        image,
        payload,
    ):
        data = payload.model_dump(
            exclude_unset=True,
        )

        if data.get("is_cover") is True:
            await self.repo.clear_cover(
                db,
                image.school_id,
            )

        for field, value in data.items():
            setattr(
                image,
                field,
                value,
            )

        return await self.repo.save(
            db,
            image,
        )

    async def reorder_images(
        self,
        db,
        school_id,
        image_ids,
    ):
        images = await self.repo.get_all_for_admin(
            db,
            school_id,
        )

        image_map = {image.id: image for image in images}

        for index, image_id in enumerate(image_ids, start=1):
            image = image_map.get(image_id)

            if image:
                image.display_order = index
                await self.repo.save(
                    db,
                    image,
                )

        return await self.repo.get_all_for_admin(
            db,
            school_id,
        )

    async def delete_image(
        self,
        db,
        image,
    ):
        await self.repo.delete(
            db,
            image,
        )
