import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketplace.digital_product import DigitalProduct
from app.models.marketplace.listing import (
    ListingStatus,
    ListingType,
    MarketplaceListing,
)
from app.models.marketplace.listing_image import ListingImage
from app.models.marketplace.physical_product import PhysicalProduct
from app.models.marketplace.service import MarketplaceService
from app.repositories.marketplace.category import CategoryRepository
from app.repositories.marketplace.listing import ListingRepository
from app.schemas.marketplace.listing import (
    DigitalProductCreate,
    ListingCreate,
    ListingImageCreate,
    ListingUpdate,
    PhysicalProductCreate,
    ServiceCreate,
)


class ListingService:
    def __init__(
        self,
        listing_repository: ListingRepository | None = None,
        category_repository: CategoryRepository | None = None,
    ):
        self.listing_repository = listing_repository or ListingRepository()

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
        title: str,
    ) -> str:
        base_slug = self._slugify(title)

        if not base_slug:
            base_slug = "listing"

        slug = base_slug
        counter = 2

        while await self.listing_repository.slug_exists(
            db,
            slug,
        ):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    async def create(
        self,
        db: AsyncSession,
        vendor_id: uuid.UUID,
        data: ListingCreate,
    ) -> MarketplaceListing:
        category = await self.category_repository.get_by_id(
            db,
            data.category_id,
        )

        if not category:
            raise ValueError("Marketplace category not found.")

        if not category.is_active:
            raise ValueError("This marketplace category is inactive.")

        slug = await self._generate_unique_slug(
            db,
            data.title,
        )

        listing = MarketplaceListing(
            vendor_id=vendor_id,
            category_id=data.category_id,
            listing_type=data.listing_type,
            title=data.title.strip(),
            slug=slug,
            description=data.description,
            price=data.price,
            currency=data.currency.upper(),
            status=ListingStatus.DRAFT,
        )

        return await self.listing_repository.create(
            db,
            listing,
        )

    async def update(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
        data: ListingUpdate,
    ) -> MarketplaceListing:
        update_data = data.model_dump(
            exclude_unset=True,
        )

        if "category_id" in update_data:
            category = await self.category_repository.get_by_id(
                db,
                update_data["category_id"],
            )

            if not category:
                raise ValueError("Marketplace category not found.")

            if not category.is_active:
                raise ValueError("This marketplace category is inactive.")

        if "title" in update_data:
            new_title = update_data.pop("title")

            if new_title != listing.title:
                listing.title = new_title

                listing.slug = await self._generate_unique_slug(
                    db,
                    new_title,
                )

        if "currency" in update_data:
            update_data["currency"] = update_data["currency"].upper()

        for field, value in update_data.items():
            setattr(listing, field, value)

        return await self.listing_repository.save(
            db,
            listing,
        )

    async def get_by_id(
        self,
        db: AsyncSession,
        listing_id: uuid.UUID,
    ) -> MarketplaceListing | None:
        return await self.listing_repository.get_by_id(
            db,
            listing_id,
        )

    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str,
    ) -> MarketplaceListing | None:
        return await self.listing_repository.get_by_slug(
            db,
            slug,
        )

    async def get_vendor_listings(
        self,
        db: AsyncSession,
        vendor_id: uuid.UUID,
    ) -> list[MarketplaceListing]:
        return await self.listing_repository.get_vendor_listings(
            db,
            vendor_id,
        )

    async def get_public_listings(
        self,
        db: AsyncSession,
        listing_type: ListingType | None = None,
        category_id: uuid.UUID | None = None,
    ) -> list[MarketplaceListing]:
        return await self.listing_repository.get_public_listings(
            db,
            listing_type=listing_type,
            category_id=category_id,
        )

    async def activate(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
    ) -> MarketplaceListing:
        listing.status = ListingStatus.ACTIVE

        return await self.listing_repository.save(
            db,
            listing,
        )

    async def deactivate(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
    ) -> MarketplaceListing:
        listing.status = ListingStatus.INACTIVE

        return await self.listing_repository.save(
            db,
            listing,
        )

    async def archive(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
    ) -> MarketplaceListing:
        listing.status = ListingStatus.ARCHIVED

        return await self.listing_repository.save(
            db,
            listing,
        )

    async def add_physical_details(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
        data: PhysicalProductCreate,
    ) -> PhysicalProduct:
        if listing.listing_type != ListingType.PHYSICAL:
            raise ValueError("Physical details can only be added to physical listings.")

        if listing.physical:
            raise ValueError("Physical details already exist.")

        physical = PhysicalProduct(
            listing_id=listing.id,
            sku=data.sku,
            stock_quantity=data.stock_quantity,
            weight_kg=data.weight_kg,
            dimensions=data.dimensions,
        )

        db.add(physical)

        await db.flush()

        return physical

    async def add_service_details(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
        data: ServiceCreate,
    ) -> MarketplaceService:
        if listing.listing_type != ListingType.SERVICE:
            raise ValueError("Service details can only be added to service listings.")

        if listing.service:
            raise ValueError("Service details already exist.")

        service = MarketplaceService(
            listing_id=listing.id,
            pricing_model=data.pricing_model,
            duration_minutes=data.duration_minutes,
            service_area=data.service_area,
            availability=data.availability,
        )

        db.add(service)

        await db.flush()

        return service

    async def add_digital_details(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
        data: DigitalProductCreate,
    ) -> DigitalProduct:
        if listing.listing_type != ListingType.DIGITAL:
            raise ValueError("Digital details can only be added to digital listings.")

        if listing.digital:
            raise ValueError("Digital details already exist.")

        digital = DigitalProduct(
            listing_id=listing.id,
            file_url=data.file_url,
            file_type=data.file_type,
            access_type=data.access_type,
            instructions=data.instructions,
        )

        db.add(digital)

        await db.flush()

        return digital

    async def add_image(
        self,
        db: AsyncSession,
        listing: MarketplaceListing,
        data: ListingImageCreate,
    ) -> ListingImage:
        if data.is_primary:
            for image in listing.images:
                image.is_primary = False

        image = ListingImage(
            listing_id=listing.id,
            image_url=data.image_url,
            is_primary=data.is_primary,
            sort_order=data.sort_order,
        )

        db.add(image)

        await db.flush()

        return image
