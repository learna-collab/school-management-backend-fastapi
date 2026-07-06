from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import DBSession, RequireSuperAdmin
from app.db.database import get_db
from app.schemas.lesson import LessonCreate, LessonUpdate
from app.schemas.school import SchoolCreate
from app.services.admin_service import AdminService
from app.services.lesson_service import lesson_service
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
@router.get("/schools")
async def get_schools(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    _: RequireSuperAdmin,
):
    schools = await service.get_schools(db)

    return {
        "schools": schools,
    }


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


@router.post("/lessons")
async def create_lesson(
    payload: LessonCreate,
    db: DBSession,
    user: RequireSuperAdmin,
):
    return await lesson_service.create_lesson(
        db,
        payload,
        str(user.id),
    )


@router.patch("/lessons/{lesson_id}")
async def update_lesson(
    lesson_id: str,
    payload: LessonUpdate,
    db: DBSession,
    _: RequireSuperAdmin,
):
    lesson = await lesson_service.update_lesson(
        db,
        lesson_id,
        payload,
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found",
        )

    return lesson


@router.get("/lessons")
async def get_all_lessons(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await lesson_service.get_all_lessons(
        db,
    )


@router.get("/lessons/{lesson_id}")
async def get_lesson(
    lesson_id: str,
    db: DBSession,
    _: RequireSuperAdmin,
):
    lesson = await lesson_service.get_lesson_by_id(
        db,
        lesson_id,
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found",
        )

    return lesson


@router.get("/lessons/search")
async def search_lessons(
    db: DBSession,
    _: RequireSuperAdmin,
    class_name: str,
    subject_name: str,
    session_name: str,
    term_name: str,
):
    return await lesson_service.get_lessons_filtered(
        db,
        class_name=class_name,
        subject_name=subject_name,
        session_name=session_name,
        term_name=term_name,
    )


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
