from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import DBSession, RequireSchoolAdmin
from app.db.database import get_db
from app.schemas.registration import (
    ParentRegistrationCreate,
    StudentRegistrationCreate,
    TeacherRegistrationCreate,
)
from app.services.excel_export_service import excel_export_service
from app.services.excel_import_service import excel_import_service
from app.services.excel_template_service import (
    excel_template_service,
)
from app.services.registration_service import registration_service
from app.services.school_service import SchoolService

router = APIRouter(
    prefix="/admin/registration",
    tags=["School Admin Registration"],
)

school_service = SchoolService()


# ======================================================
# HELPER
# ======================================================


async def get_school(db, admin):
    school = await school_service.get_by_id(
        db,
        admin.school_id,
    )

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found.",
        )

    return school


# ======================================================
# SINGLE STUDENT
# ======================================================


@router.post("/student")
async def register_student(
    payload: StudentRegistrationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: RequireSchoolAdmin,
):
    school = await get_school(db, admin)

    result = await registration_service.register_student(
        db=db,
        school_id=school.id,
        payload=payload,
    )

    return {
        "message": "Student registered successfully.",
        "credentials": {
            "username": result["username"],
            "password": result["password"],
        },
    }


# ======================================================
# SINGLE TEACHER
# ======================================================


@router.post("/teacher")
async def register_teacher(
    payload: TeacherRegistrationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: RequireSchoolAdmin,
):
    school = await get_school(db, admin)

    result = await registration_service.register_teacher(
        db=db,
        school_id=school.id,
        payload=payload,
    )

    return {
        "message": "Teacher registered successfully.",
        "credentials": {
            "username": result["username"],
            "password": result["password"],
        },
    }


# ======================================================
# SINGLE PARENT
# ======================================================


@router.post("/parent")
async def register_parent(
    payload: ParentRegistrationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: RequireSchoolAdmin,
):
    school = await get_school(db, admin)

    result = await registration_service.register_parent(
        db=db,
        school_id=school.id,
        payload=payload,
    )

    return {
        "message": "Parent registered successfully.",
        "credentials": {
            "username": result["username"],
            "password": result["password"],
        },
    }


# ======================================================
# BATCH STUDENTS
# ======================================================


@router.post("/students/batch")
async def register_students_batch(
    payload: list[StudentRegistrationCreate],
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: RequireSchoolAdmin,
):
    school = await get_school(db, admin)

    result = await registration_service.register_students_batch(
        db=db,
        school_id=school.id,
        payloads=payload,
    )

    return {
        "message": f"{len(result)} students registered successfully.",
        "users": result,
    }


# ======================================================
# BATCH TEACHERS
# ======================================================


@router.post("/teachers/batch")
async def register_teachers_batch(
    payload: list[TeacherRegistrationCreate],
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: RequireSchoolAdmin,
):
    school = await get_school(db, admin)

    result = await registration_service.register_teachers_batch(
        db=db,
        school_id=school.id,
        payloads=payload,
    )

    return {
        "message": f"{len(result)} teachers registered successfully.",
        "users": result,
    }


# ======================================================
# BATCH PARENTS
# ======================================================


@router.post("/parents/batch")
async def register_parents_batch(
    payload: list[ParentRegistrationCreate],
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: RequireSchoolAdmin,
):
    school = await get_school(db, admin)

    result = await registration_service.register_parents_batch(
        db=db,
        school_id=school.id,
        payloads=payload,
    )

    return {
        "message": f"{len(result)} parents registered successfully.",
        "users": result,
    }


@router.post("/students/import")
async def import_students(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: RequireSchoolAdmin = None,
):
    school = await get_school(
        db,
        admin,
    )

    rows = excel_import_service.read_students(
        await file.read(),
    )

    payloads = [StudentRegistrationCreate(**row) for row in rows]

    result = await registration_service.register_students_batch(
        db=db,
        school_id=school.id,
        payloads=payloads,
    )

    excel = excel_export_service.import_report(
        credentials=result["credentials"],
        errors=result["errors"],
    )

    return StreamingResponse(
        excel,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": ("attachment; filename=student_import_report.xlsx")
        },
    )


# ======================================================
# IMPORT TEACHERS
# ======================================================


@router.post("/teachers/import")
async def import_teachers(
    admin: RequireSchoolAdmin,
    db: DBSession,
    file: Annotated[UploadFile, File()] = ...,
):
    school = await get_school(
        db,
        admin,
    )

    rows = excel_import_service.read_teachers(
        await file.read(),
    )

    payloads = [TeacherRegistrationCreate(**row) for row in rows]

    result = await registration_service.register_students_batch(
        db=db,
        school_id=school.id,
        payloads=payloads,
    )

    excel = excel_export_service.import_report(
        credentials=result["credentials"],
        errors=result["errors"],
    )

    return StreamingResponse(
        excel,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": ("attachment; filename=student_import_report.xlsx")
        },
    )


# ======================================================
# DOWNLOAD STUDENT TEMPLATE
# ======================================================


@router.get("/templates/student")
async def download_student_template(
    db: DBSession,
    admin: RequireSchoolAdmin,
):
    school = await get_school(db, admin)

    classes = await registration_service.get_school_classes(
        db=db,
        school_id=school.id,
    )

    excel = excel_template_service.student_template(classes)

    return StreamingResponse(
        excel,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=student_import_template.xlsx"
        },
    )


# ======================================================
# DOWNLOAD TEACHER TEMPLATE
# ======================================================


@router.get("/templates/teacher")
async def download_teacher_template(
    db: DBSession,
    admin: RequireSchoolAdmin,
):
    school = await get_school(db, admin)

    classes = await registration_service.get_school_classes(
        db=db,
        school_id=school.id,
    )

    excel = excel_template_service.teacher_template(classes)

    return StreamingResponse(
        excel,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=teacher_import_template.xlsx"
        },
    )
