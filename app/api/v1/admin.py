from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import DBSession, RequireSuperAdmin
from app.db.database import get_db
from app.schemas.school import SchoolCreate, SchoolUpdate
from app.services.admin_service import AdminService
from app.services.school_service import SchoolService

school_service = SchoolService()

router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
)

service = AdminService()


# =====================================================
# GET SCHOOLS
# =====================================================

# =====================================================
# IMPORT SCHOOLS FROM EXCEL
# =====================================================


@router.post("/schools/import")
async def import_schools(
    file: UploadFile = File(...),
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ] = None,
    _: RequireSuperAdmin = None,
):
    # -------------------------------------------------
    # CHECK FILE TYPE
    # -------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was uploaded.",
        )

    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx Excel files are supported.",
        )

    # -------------------------------------------------
    # IMPORT
    # -------------------------------------------------

    try:
        result = await service.import_schools_from_excel(
            db=db,
            file=file,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to import schools.",
        )

    return {
        "message": "School import completed.",
        **result,
    }


@router.get("/schools")
async def get_schools(
    db: DBSession,
    _: RequireSuperAdmin,
    search: str | None = Query(default=None),
    state: str | None = Query(default=None),
    location: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
):
    return await service.get_schools(
        db=db,
        search=search,
        state=state,
        location=location,
        page=page,
        per_page=per_page,
    )


# =====================================================
# CREATE SCHOOL
# =====================================================


@router.post("/schools")
async def create_school(
    payload: SchoolCreate,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    _: RequireSuperAdmin,
):
    result = await service.create_school(
        db,
        payload,
    )
    return {
        "message": "School created successfully.",
        "school": result["school"],
        "credentials": result["credentials"],
    }


# =====================================================
# UPDATE SCHOOL
# =====================================================


@router.put("/schools/{school_id}")
async def update_school(
    school_id: str,
    payload: SchoolUpdate,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    _: RequireSuperAdmin,
):
    school = await service.update_school(
        db,
        school_id,
        payload,
    )

    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found.",
        )

    return {
        "message": "School updated successfully.",
        "school": school,
    }


# =====================================================
# DELETE SCHOOL
# =====================================================


@router.delete("/schools/{school_id}")
async def delete_school(
    school_id: str,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    _: RequireSuperAdmin,
):
    deleted = await service.delete_school(
        db,
        school_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="School not found",
        )
    return {
        "message": "School deleted successfully",
    }


# =====================================
# DASHBOARD STATS
# =====================================


@router.post("/create-school-admin")
async def create_school_admin(
    payload: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: RequireSuperAdmin,
):
    user = await service.create_school_admin(db, payload)
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create admin")
    return {
        "message": "School admin created",
        "user": user,
    }


@router.delete("/admins/{user_id}")
async def delete_admin(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: RequireSuperAdmin,
):
    result = await service.delete_admin(db, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {
        "message": "Admin deleted",
    }


@router.get("/stats")
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: RequireSuperAdmin,
):
    return await service.get_dashboard_stats(db)


@router.get("/admins")
async def get_admins(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: RequireSuperAdmin,
):
    admins = await service.get_admins(db)
    return {
        "message": "Admins fetched successfully",
        "admins": admins,
    }


# =====================================
# ASSIGN SCHOOL ADMIN
# =====================================


@router.post("/users/{user_id}/assign-school-admin/{school_id}")
async def assign_school_admin(
    user_id: str,
    school_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: RequireSuperAdmin,
):
    user = await service.assign_school_admin(
        db,
        user_id,
        school_id,
    )
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User or School not found",
        )
    return {
        "message": "School admin assigned successfully",
        "user": user,
    }


# =====================================
# REVOKE SCHOOL ADMIN
# =====================================


@router.post("/users/{user_id}/revoke-school-admin")
async def revoke_school_admin(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: RequireSuperAdmin,
):
    user = await service.revoke_school_admin(
        db,
        user_id,
    )
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )
    return {
        "message": "School admin revoked",
        "user": user,
    }


# =====================================================
# DISABLE SCHOOL
# =====================================================


@router.patch("/schools/{school_id}/disable")
async def disable_school(
    school_id: str,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    _: RequireSuperAdmin,
):
    school = await service.disable_school(
        db,
        school_id,
    )
    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found.",
        )
    return {
        "message": "School disabled successfully.",
        "school": school,
    }


# =====================================================
# ENABLE SCHOOL
# =====================================================


@router.patch("/schools/{school_id}/enable")
async def enable_school(
    school_id: str,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    _: RequireSuperAdmin,
):
    school = await service.enable_school(
        db,
        school_id,
    )
    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found.",
        )
    return {
        "message": "School enabled successfully.",
        "school": school,
    }


@router.get("/schools/export")
async def export_schools(
    db: DBSession,
    _: RequireSuperAdmin,
    search: str | None = None,
):
    result = await service.get_schools(
        db=db,
        search=search,
        page=1,
        per_page=100000,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Schools"

    ws.append(
        [
            "School",
            "State",
            "Phone",
            "Admin",
            "Username",
            "Status",
        ]
    )

    for school in result["items"]:
        admin = school["admin"]

        ws.append(
            [
                school["name"],
                school["state"],
                school["phone"],
                f"{admin['first_name']} {admin['last_name']}",
                admin["username"],
                "Active" if school["is_active"] else "Disabled",
            ]
        )

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="schools.xlsx"'},
    )
