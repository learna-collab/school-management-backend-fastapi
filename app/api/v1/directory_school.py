from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.database import get_db
from app.schemas.directory_school import (
    DirectorySchoolDetail,
    DirectorySchoolListResponse,
)
from app.services.directory_service import DirectorySchoolService

router = APIRouter(
    prefix="/directory/schools",
    tags=["School Directory"],
)

service = DirectorySchoolService()


DBSession = Annotated[
    object,
    Depends(get_db),
]


# =====================================================
# LIST SCHOOLS
# =====================================================


@router.get(
    "",
    response_model=DirectorySchoolListResponse,
)
async def list_schools(
    db: DBSession,
    page: int = Query(
        1,
        ge=1,
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        None,
        max_length=100,
    ),
    state: str | None = Query(
        None,
        max_length=100,
    ),
    city: str | None = Query(
        None,
        max_length=100,
    ),
    school_type: str | None = Query(
        None,
        max_length=50,
    ),
    ownership_type: str | None = Query(
        None,
        max_length=50,
    ),
    verified: bool | None = Query(
        None,
    ),
):
    return await service.list_schools(
        db,
        page=page,
        page_size=page_size,
        search=search,
        state=state,
        city=city,
        school_type=school_type,
        ownership_type=ownership_type,
        verified=verified,
    )


# =====================================================
# FEATURED SCHOOLS
# =====================================================


@router.get(
    "/featured",
)
async def featured_schools(
    db: DBSession,
    limit: int = Query(
        12,
        ge=1,
        le=50,
    ),
):
    return await service.get_featured(
        db,
        limit,
    )


# =====================================================
# VERIFIED SCHOOLS
# =====================================================


@router.get(
    "/verified",
)
async def verified_schools(
    db: DBSession,
    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),
):
    return await service.get_verified(
        db,
        limit,
    )


# =====================================================
# SCHOOL DETAILS
# =====================================================


@router.get(
    "/{slug}",
    response_model=DirectorySchoolDetail,
)
async def get_school(
    slug: str,
    db: DBSession,
):
    school = await service.get_school_by_slug(
        db,
        slug,
    )

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found",
        )

    return school
