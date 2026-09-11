from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.deps import DBSession, RequireVendor
from app.models.marketplace.vendor import VendorStatus
from app.schemas.marketplace.listing import (
    DigitalProductCreate,
    DigitalProductResponse,
    ListingCreate,
    ListingImageCreate,
    ListingImageResponse,
    ListingResponse,
    ListingUpdate,
    PhysicalProductCreate,
    PhysicalProductResponse,
    ServiceCreate,
    ServiceResponse,
)
from app.schemas.marketplace.vendor import (
    VendorCreate,
    VendorResponse,
    VendorUpdate,
)
from app.services.marketplace.listing import ListingService
from app.services.marketplace.vendor import VendorService

router = APIRouter(
    prefix="/marketplace/vendor",
    tags=["Marketplace Vendor"],
)

vendor_service = VendorService()
listing_service = ListingService()


# ============================================================
# HELPERS
# ============================================================


async def get_vendor(
    db: DBSession,
    user: RequireVendor,
):
    """
    Get the vendor profile belonging to the authenticated
    VENDOR user.
    """
    vendor = await vendor_service.get_by_user_id(
        db,
        user.id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor profile not found",
        )

    return vendor


async def get_own_vendor_listing(
    db: DBSession,
    user: RequireVendor,
    listing_id: UUID,
):
    """Get a listing only if it belongs to the authenticated vendor."""
    vendor = await get_vendor(
        db,
        user,
    )

    listing = await listing_service.get_by_id(
        db,
        listing_id,
    )

    if not listing:
        raise HTTPException(
            status_code=404,
            detail="Listing not found",
        )

    if listing.vendor_id != vendor.id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this listing",
        )

    return vendor, listing


# ============================================================
# VENDOR PROFILE
# ============================================================


@router.post(
    "/profile",
    response_model=VendorResponse,
)
async def create_vendor_profile(
    payload: VendorCreate,
    db: DBSession,
    user: RequireVendor,
):
    """
    Create the vendor profile for the authenticated VENDOR user.
    """
    existing = await vendor_service.get_by_user_id(
        db,
        user.id,
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Vendor profile already exists",
        )

    return await vendor_service.create_profile(
        db=db,
        user=user,
        data=payload,
    )


@router.get(
    "/profile",
    response_model=VendorResponse,
)
async def get_vendor_profile(
    db: DBSession,
    user: RequireVendor,
):
    return await get_vendor(
        db,
        user,
    )


@router.patch(
    "/profile",
    response_model=VendorResponse,
)
async def update_vendor_profile(
    payload: VendorUpdate,
    db: DBSession,
    user: RequireVendor,
):
    vendor = await get_vendor(
        db,
        user,
    )

    return await vendor_service.update_profile(
        db=db,
        vendor=vendor,
        data=payload,
    )


# ============================================================
# LISTINGS
# ============================================================


@router.post(
    "/listings",
    response_model=ListingResponse,
)
async def create_listing(
    payload: ListingCreate,
    db: DBSession,
    user: RequireVendor,
):
    """
    Create a new marketplace listing.

    New listings always start as DRAFT.
    """
    vendor = await get_vendor(
        db,
        user,
    )

    return await listing_service.create(
        db=db,
        vendor=vendor,
        data=payload,
    )


@router.get(
    "/listings",
    response_model=list[ListingResponse],
)
async def get_vendor_listings(
    db: DBSession,
    user: RequireVendor,
):
    vendor = await get_vendor(
        db,
        user,
    )

    return await listing_service.get_vendor_listings(
        db,
        vendor.id,
    )


@router.get(
    "/listings/{listing_id}",
    response_model=ListingResponse,
)
async def get_vendor_listing(
    listing_id: UUID,
    db: DBSession,
    user: RequireVendor,
):
    _, listing = await get_own_vendor_listing(
        db,
        user,
        listing_id,
    )

    return listing


@router.patch(
    "/listings/{listing_id}",
    response_model=ListingResponse,
)
async def update_vendor_listing(
    listing_id: UUID,
    payload: ListingUpdate,
    db: DBSession,
    user: RequireVendor,
):
    _, listing = await get_own_vendor_listing(
        db,
        user,
        listing_id,
    )

    return await listing_service.update(
        db=db,
        listing=listing,
        data=payload,
    )


# ============================================================
# PHYSICAL PRODUCT
# ============================================================


@router.post(
    "/listings/{listing_id}/physical",
    response_model=PhysicalProductResponse,
)
async def add_physical_product(
    listing_id: UUID,
    payload: PhysicalProductCreate,
    db: DBSession,
    user: RequireVendor,
):
    _, listing = await get_own_vendor_listing(
        db,
        user,
        listing_id,
    )

    return await listing_service.add_physical_details(
        db=db,
        listing=listing,
        data=payload,
    )


# ============================================================
# SERVICE
# ============================================================


@router.post(
    "/listings/{listing_id}/service",
    response_model=ServiceResponse,
)
async def add_service(
    listing_id: UUID,
    payload: ServiceCreate,
    db: DBSession,
    user: RequireVendor,
):
    _, listing = await get_own_vendor_listing(
        db,
        user,
        listing_id,
    )

    return await listing_service.add_service_details(
        db=db,
        listing=listing,
        data=payload,
    )


# ============================================================
# DIGITAL PRODUCT
# ============================================================


@router.post(
    "/listings/{listing_id}/digital",
    response_model=DigitalProductResponse,
)
async def add_digital_product(
    listing_id: UUID,
    payload: DigitalProductCreate,
    db: DBSession,
    user: RequireVendor,
):
    _, listing = await get_own_vendor_listing(
        db,
        user,
        listing_id,
    )

    return await listing_service.add_digital_details(
        db=db,
        listing=listing,
        data=payload,
    )


# ============================================================
# IMAGES
# ============================================================


@router.post(
    "/listings/{listing_id}/images",
    response_model=ListingImageResponse,
)
async def add_listing_image(
    listing_id: UUID,
    payload: ListingImageCreate,
    db: DBSession,
    user: RequireVendor,
):
    _, listing = await get_own_vendor_listing(
        db,
        user,
        listing_id,
    )

    return await listing_service.add_image(
        db=db,
        listing=listing,
        data=payload,
    )


# ============================================================
# LISTING STATUS
# ============================================================


@router.post(
    "/listings/{listing_id}/activate",
    response_model=ListingResponse,
)
async def activate_listing(
    listing_id: UUID,
    db: DBSession,
    user: RequireVendor,
):
    vendor, listing = await get_own_vendor_listing(
        db,
        user,
        listing_id,
    )

    if vendor.status != VendorStatus.APPROVED:
        raise HTTPException(
            status_code=403,
            detail=("Your vendor account must be approved before publishing listings"),
        )

    if not vendor.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your vendor account is not active",
        )

    return await listing_service.activate(
        db,
        listing,
    )


@router.post(
    "/listings/{listing_id}/deactivate",
    response_model=ListingResponse,
)
async def deactivate_listing(
    listing_id: UUID,
    db: DBSession,
    user: RequireVendor,
):
    _, listing = await get_own_vendor_listing(
        db,
        user,
        listing_id,
    )

    return await listing_service.deactivate(
        db,
        listing,
    )


@router.post(
    "/listings/{listing_id}/archive",
    response_model=ListingResponse,
)
async def archive_listing(
    listing_id: UUID,
    db: DBSession,
    user: RequireVendor,
):
    _, listing = await get_own_vendor_listing(
        db,
        user,
        listing_id,
    )

    return await listing_service.archive(
        db,
        listing,
    )
