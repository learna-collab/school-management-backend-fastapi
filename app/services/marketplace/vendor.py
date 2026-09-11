import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketplace.vendor import (
    Vendor,
    VendorStatus,
    VendorType,
)
from app.models.user import User, UserRole
from app.repositories.marketplace.vendor import VendorRepository
from app.schemas.marketplace.vendor import (
    VendorCreate,
    VendorUpdate,
)


class VendorService:
    def __init__(
        self,
        vendor_repository: VendorRepository | None = None,
    ):
        self.vendor_repository = vendor_repository or VendorRepository()

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
        store_name: str,
    ) -> str:
        base_slug = self._slugify(store_name)

        if not base_slug:
            base_slug = "vendor"

        slug = base_slug
        counter = 2

        while await self.vendor_repository.slug_exists(
            db,
            slug,
        ):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    async def get_by_id(
        self,
        db: AsyncSession,
        vendor_id: uuid.UUID,
    ) -> Vendor | None:
        return await self.vendor_repository.get_by_id(
            db,
            vendor_id,
        )

    async def get_by_user_id(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> Vendor | None:
        return await self.vendor_repository.get_by_user_id(
            db,
            user_id,
        )

    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str,
    ) -> Vendor | None:
        return await self.vendor_repository.get_by_slug(
            db,
            slug,
        )

    async def create_profile(
        self,
        db: AsyncSession,
        user: User,
        data: VendorCreate,
    ) -> Vendor:
        existing_vendor = await self.vendor_repository.get_by_user_id(
            db,
            user.id,
        )

        if existing_vendor:
            raise ValueError("Vendor profile already exists for this account.")

        slug = await self._generate_unique_slug(
            db,
            data.store_name,
        )

        vendor = Vendor(
            user_id=user.id,
            vendor_type=data.vendor_type,
            store_name=data.store_name,
            business_name=data.business_name,
            slug=slug,
            description=data.description,
            phone=data.phone,
            public_email=(str(data.public_email) if data.public_email else None),
            address=data.address,
            logo_url=data.logo_url,
            status=VendorStatus.PENDING,
        )

        return await self.vendor_repository.create(
            db,
            vendor,
        )

    async def update_profile(
        self,
        db: AsyncSession,
        vendor: Vendor,
        data: VendorUpdate,
    ) -> Vendor:
        update_data = data.model_dump(
            exclude_unset=True,
        )

        if "store_name" in update_data:
            new_store_name = update_data.pop("store_name")

            if new_store_name != vendor.store_name:
                vendor.store_name = new_store_name

                vendor.slug = await self._generate_unique_slug(
                    db,
                    new_store_name,
                )

        if "public_email" in update_data:
            email = update_data["public_email"]

            update_data["public_email"] = str(email) if email else None

        for field, value in update_data.items():
            setattr(vendor, field, value)

        return await self.vendor_repository.save(
            db,
            vendor,
        )

    async def approve(
        self,
        db: AsyncSession,
        vendor: Vendor,
    ) -> Vendor:
        if vendor.status == VendorStatus.APPROVED:
            return vendor

        if vendor.status == VendorStatus.SUSPENDED:
            raise ValueError("A suspended vendor cannot be approved directly.")

        vendor.status = VendorStatus.APPROVED
        vendor.is_active = True

        return await self.vendor_repository.save(
            db,
            vendor,
        )

    async def reject(
        self,
        db: AsyncSession,
        vendor: Vendor,
    ) -> Vendor:
        vendor.status = VendorStatus.REJECTED

        return await self.vendor_repository.save(
            db,
            vendor,
        )

    async def suspend(
        self,
        db: AsyncSession,
        vendor: Vendor,
    ) -> Vendor:
        vendor.status = VendorStatus.SUSPENDED
        vendor.is_active = False

        return await self.vendor_repository.save(
            db,
            vendor,
        )

    async def reactivate(
        self,
        db: AsyncSession,
        vendor: Vendor,
    ) -> Vendor:
        if vendor.status != VendorStatus.SUSPENDED:
            raise ValueError("Only suspended vendors can be reactivated.")

        vendor.status = VendorStatus.APPROVED
        vendor.is_active = True

        return await self.vendor_repository.save(
            db,
            vendor,
        )
