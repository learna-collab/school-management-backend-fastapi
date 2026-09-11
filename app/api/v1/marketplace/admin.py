from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import DBSession, RequireSuperAdmin
from app.models.marketplace.vendor import VendorStatus
from app.schemas.marketplace.vendor import VendorResponse
from app.services.marketplace.vendor import VendorService

router = APIRouter(
    prefix="/marketplace/admin",
    tags=["Marketplace Admin"],
)

vendor_service = VendorService()


# ============================================================
# VENDORS
# ============================================================


@router.get(
    "/vendors",
    response_model=list[VendorResponse],
)
async def get_vendors(
    db: DBSession,
    _: RequireSuperAdmin,
    status: VendorStatus | None = Query(default=None),
):
    """
    Get marketplace vendors.

    Superadmin can optionally filter by vendor status.
    """
    vendors, _ = await vendor_service.vendor_repository.list_all(
        db=db,
        status=status,
    )

    return vendors


@router.get(
    "/vendors/pending",
    response_model=list[VendorResponse],
)
async def get_pending_vendors(
    db: DBSession,
    _: RequireSuperAdmin,
):
    vendors, _ = await vendor_service.vendor_repository.list_pending(
        db,
    )

    return vendors


@router.get(
    "/vendors/{vendor_id}",
    response_model=VendorResponse,
)
async def get_vendor(
    vendor_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    vendor = await vendor_service.get_by_id(
        db,
        vendor_id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    return vendor


# ============================================================
# APPROVAL
# ============================================================


@router.post(
    "/vendors/{vendor_id}/approve",
    response_model=VendorResponse,
)
async def approve_vendor(
    vendor_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    vendor = await vendor_service.get_by_id(
        db,
        vendor_id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    return await vendor_service.approve(
        db,
        vendor,
    )


# ============================================================
# REJECTION
# ============================================================


@router.post(
    "/vendors/{vendor_id}/reject",
    response_model=VendorResponse,
)
async def reject_vendor(
    vendor_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    vendor = await vendor_service.get_by_id(
        db,
        vendor_id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    return await vendor_service.reject(
        db,
        vendor,
    )


# ============================================================
# SUSPENSION
# ============================================================


@router.post(
    "/vendors/{vendor_id}/suspend",
    response_model=VendorResponse,
)
async def suspend_vendor(
    vendor_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    vendor = await vendor_service.get_by_id(
        db,
        vendor_id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    return await vendor_service.suspend(
        db,
        vendor,
    )


# ============================================================
# REACTIVATE
# ============================================================


@router.post(
    "/vendors/{vendor_id}/reactivate",
    response_model=VendorResponse,
)
async def reactivate_vendor(
    vendor_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    vendor = await vendor_service.get_by_id(
        db,
        vendor_id,
    )

    if not vendor:
        raise HTTPException(
            status_code=404,
            detail="Vendor not found",
        )

    return await vendor_service.reactivate(
        db,
        vendor,
    )
