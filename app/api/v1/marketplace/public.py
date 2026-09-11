from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import DBSession
from app.models.marketplace.listing import ListingType
from app.models.marketplace.vendor import VendorStatus
from app.schemas.marketplace.category import CategoryResponse
from app.schemas.marketplace.listing import ListingResponse
from app.schemas.marketplace.vendor import VendorPublicResponse
from app.services.marketplace.category import CategoryService
from app.services.marketplace.listing import ListingService
from app.services.marketplace.vendor import VendorService

router = APIRouter(
    prefix="/marketplace",
    tags=["Marketplace"],
)


vendor_service = VendorService()
category_service = CategoryService()
listing_service = ListingService()


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
)
async def get_categories(
    db: DBSession,
):
    return await category_service.list_active(
        db,
    )


@router.get(
    "/categories/{slug}",
    response_model=CategoryResponse,
)
async def get_category(
    slug: str,
    db: DBSession,
):
    category = await category_service.get_by_slug(
        db,
        slug,
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    if not category.is_active:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    return category


@router.get(
    "/categories/{slug}/listings",
    response_model=list[ListingResponse],
)
async def get_category_listings(
    slug: str,
    db: DBSession,
):
    category = await category_service.get_by_slug(
        db,
        slug,
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    if not category.is_active:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    return await listing_service.get_public_listings(
        db=db,
        category_id=category.id,
    )


@router.get(
    "/stores/{slug}",
    response_model=VendorPublicResponse,
)
async def get_store(
    slug: str,
    db: DBSession,
):
    vendor = await vendor_service.get_by_slug(
        db,
        slug,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Store not found",
        )

    if vendor.status != VendorStatus.APPROVED or not vendor.is_active:
        raise HTTPException(
            status_code=404,
            detail="Store not found",
        )

    return vendor


@router.get(
    "/listings",
    response_model=list[ListingResponse],
)
async def get_marketplace_listings(
    db: DBSession,
    listing_type: ListingType | None = Query(
        default=None,
        description="Filter by PHYSICAL, SERVICE or DIGITAL",
    ),
    category_id: UUID | None = Query(
        default=None,
    ),
):
    return await listing_service.get_public_listings(
        db=db,
        listing_type=listing_type,
        category_id=category_id,
    )


@router.get(
    "/listings/{slug}",
    response_model=ListingResponse,
)
async def get_marketplace_listing(
    slug: str,
    db: DBSession,
):
    listing = await listing_service.get_by_slug(
        db,
        slug,
    )

    if not listing:
        raise HTTPException(
            status_code=404,
            detail="Listing not found",
        )

    if listing.status.value != "ACTIVE":
        raise HTTPException(
            status_code=404,
            detail="Listing not found",
        )

    if (
        not listing.vendor
        or listing.vendor.status.value != "APPROVED"
        or not listing.vendor.is_active
    ):
        raise HTTPException(
            status_code=404,
            detail="Listing not found",
        )

    return listing


@router.get(
    "/stores/{slug}/listings",
    response_model=list[ListingResponse],
)
async def get_store_listings(
    slug: str,
    db: DBSession,
):
    vendor = await vendor_service.get_by_slug(
        db,
        slug,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Store not found",
        )

    if vendor.status.value != "APPROVED" or not vendor.is_active:
        raise HTTPException(
            status_code=404,
            detail="Store not found",
        )

    return await listing_service.listing_repository.get_vendor_public_listings(
        db,
        vendor.id,
    )
