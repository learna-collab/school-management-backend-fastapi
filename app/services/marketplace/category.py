import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketplace.category import MarketplaceCategory
from app.repositories.marketplace.category import CategoryRepository
from app.schemas.marketplace.category import (
    CategoryCreate,
    CategoryUpdate,
)


class CategoryService:
    def __init__(
        self,
        category_repository: CategoryRepository | None = None,
    ):
        self.category_repository = category_repository or CategoryRepository()

    @staticmethod
    def _slugify(value: str) -> str:
        value = value.strip().lower()

        value = re.sub(
            r"[^a-z0-9\s-]",
            "",
            value,
        )

        value = re.sub(
            r"[\s-]+",
            "-",
            value,
        )

        return value.strip("-")

    async def _generate_unique_slug(
        self,
        db: AsyncSession,
        name: str,
    ) -> str:
        base_slug = self._slugify(name)

        if not base_slug:
            base_slug = "category"

        slug = base_slug
        counter = 2

        while await self.category_repository.get_by_slug(
            db,
            slug,
        ):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    async def create(
        self,
        db: AsyncSession,
        data: CategoryCreate,
    ) -> MarketplaceCategory:
        slug = await self._generate_unique_slug(
            db,
            data.name,
        )

        category = MarketplaceCategory(
            name=data.name.strip(),
            slug=slug,
            description=data.description,
            is_active=True,
        )

        return await self.category_repository.create(
            db,
            category,
        )

    async def get_by_id(
        self,
        db: AsyncSession,
        category_id: uuid.UUID,
    ) -> MarketplaceCategory | None:
        return await self.category_repository.get_by_id(
            db,
            category_id,
        )

    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str,
    ) -> MarketplaceCategory | None:
        return await self.category_repository.get_by_slug(
            db,
            slug,
        )

    async def list_active(
        self,
        db: AsyncSession,
    ) -> list[MarketplaceCategory]:
        return await self.category_repository.list_active(db)

    async def list_all(
        self,
        db: AsyncSession,
    ) -> list[MarketplaceCategory]:
        return await self.category_repository.list_all(db)

    async def update(
        self,
        db: AsyncSession,
        category: MarketplaceCategory,
        data: CategoryUpdate,
    ) -> MarketplaceCategory:
        update_data = data.model_dump(
            exclude_unset=True,
        )

        if "name" in update_data:
            new_name = update_data.pop("name")

            if new_name != category.name:
                category.name = new_name

                category.slug = await self._generate_unique_slug(
                    db,
                    new_name,
                )

        for field, value in update_data.items():
            setattr(category, field, value)

        return await self.category_repository.save(
            db,
            category,
        )
