from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, DBSession, RequireSchoolAdmin
from app.db.database import get_db
from app.schemas.academic_session import AcademicSessionCreate
from app.schemas.attendance import AttendanceAnalyticsResponse
from app.schemas.result_responses import (
    ApprovalHistoryItem,
    ClassResultResponse,
)
from app.schemas.result_schema import (
    RejectResultRequest,
    UpdateResultRecord,
)
from app.schemas.school import SchoolOnboardingRequest
from app.schemas.school_admin import (
    UpdateClassRequest,
    UpdateStudentRequest,
    UpdateSubjectRequest,
    UpdateTeacherRequest,
)
from app.schemas.subject import CreateSubjectRequest
from app.schemas.teacher_assignmet import CreateClassRequest, PromoteStudentsRequest
from app.schemas.term import TermCreate
from app.services.attendance_service import attendance_service
from app.services.result_service import result_service
from app.services.school_admin_dashboard_service import school_admin_dashboard_service
from app.services.school_admin_service import school_admin_service
from app.services.school_assignment_service import school_assignment_service
from app.services.school_class_service import school_class_service
from app.services.school_service import SchoolService
from app.services.subject_service import subject_service

router = APIRouter(
    prefix="/school-admin",
    tags=["School Admin"],
)

school_service = SchoolService()


# =====================================================
# 📊 DASHBOARD / STATS
# =====================================================
@router.get("/stats")
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: RequireSchoolAdmin,
):
    return await school_admin_service.get_stats(db, str(user.school_id))


# =====================================================
# 🏫 SCHOOL ONBOARDING
# =====================================================
@router.post("/onboard")
async def onboard_school(
    payload: SchoolOnboardingRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await school_service.onboard_school(db, payload)

    return {
        "message": "School registered successfully",
        "school_code": result["school"].code,
        "slug": result["school"].slug,
    }


# =====================================================
# 📚 SUBJECTS
# ====================================================


@router.post("/subjects")
async def create_subject(
    payload: CreateSubjectRequest,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await subject_service.create_subject(
        db=db,
        name=payload.name,
        code=payload.code,
        school_id=user.school_id,
    )


@router.get("/subjects")
async def get_subjects(
    db: DBSession,
    user: CurrentUser,
):
    return await subject_service.get_school_subjects(
        db,
        user.school_id,
    )


@router.get("/classes/{class_id}/subjects")
async def get_class_subjects(
    class_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await subject_service.get_class_subjects(
        db=db,
        class_id=class_id,
        school_id=user.school_id,
    )


@router.post("/classes/{class_id}/subjects/{subject_id}")
async def assign_subject_to_class(
    class_id: UUID,
    subject_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await subject_service.assign_subject_to_class(
        db=db,
        class_id=class_id,
        subject_id=subject_id,
        school_id=user.school_id,
    )


@router.delete("/classes/{class_id}/subjects/{subject_id}")
async def remove_subject_from_class(
    class_id: UUID,
    subject_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    result = await subject_service.remove_subject_from_class(
        db=db,
        class_id=class_id,
        subject_id=subject_id,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail="Subject assignment not found",
        )

    return {
        "message": "Subject removed from class",
    }


# =====================================================
# 📊 LESSONS (LMS CORE)
# =====================================================


# =====================================================
# RESULTS
# =====================================================
@router.get(
    "/results/class",
    response_model=ClassResultResponse,
)
async def get_class_results(
    class_id: UUID,
    session_id: UUID | None,
    term_id: UUID | None,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await result_service.get_class_results(
        db=db,
        school_id=user.school_id,
        class_id=class_id,
        session_id=session_id,
        term_id=term_id,
    )


@router.get(
    "/results/class/{class_id}/batches",
)
async def get_class_batches(
    class_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await result_service.get_class_batches(
        db=db,
        class_id=class_id,
        school_id=user.school_id,
    )


@router.get(
    "/results/{batch_id}",
)
async def get_batch(
    batch_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await result_service.get_batch_admin(
        db=db,
        batch_id=batch_id,
        school_id=user.school_id,
    )


@router.get(
    "/results/{batch_id}/view",
    response_model=ClassResultResponse,
)
async def view_batch(
    batch_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await result_service.view_batch_admin(
        db=db,
        batch_id=batch_id,
        school_id=user.school_id,
    )


@router.post(
    "/results/{batch_id}/approve",
)
async def approve_result(
    batch_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await result_service.approve_result(
        db=db,
        batch_id=batch_id,
        admin=user,
    )


@router.post(
    "/results/{batch_id}/reject",
)
async def reject_result(
    batch_id: UUID,
    payload: RejectResultRequest,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await result_service.reject_result(
        db=db,
        batch_id=batch_id,
        note=payload.note,
        admin=user,
    )


@router.post(
    "/results/{batch_id}/publish",
)
async def publish_result(
    batch_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await result_service.publish_result(
        db=db,
        batch_id=batch_id,
        admin=user,
    )


@router.patch(
    "/results/records/{record_id}",
)
async def update_result_record(
    record_id: UUID,
    payload: UpdateResultRecord,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await result_service.update_result_record(
        db=db,
        record_id=record_id,
        payload=payload,
        user=user,
    )


@router.get(
    "/results/{batch_id}/history",
    response_model=list[ApprovalHistoryItem],
)
async def approval_history(
    batch_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await result_service.get_approval_history(
        db=db,
        batch_id=batch_id,
        school_id=user.school_id,
    )


# =====================================================
# 📊 ATTENDANCE
# =====================================================


@router.get("/attendance/student/{student_id}")
async def student_attendance(
    student_id: str,
    session_id: str,
    term_id: str,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    return await attendance_service.get_student_attendance(
        db,
        student_id,
        session_id,
        term_id,
    )


@router.get(
    "/attendance/dashboard",
)
async def attendance_dashboard(
    attendance_date: date,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await attendance_service.get_dashboard(
        db=db,
        school_id=user.school_id,
        attendance_date=attendance_date,
    )


@router.get(
    "/attendance/class",
)
async def get_class_attendance(
    class_id: UUID,
    attendance_date: date,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await attendance_service.get_class_attendance(
        teacher=user,
        db=db,
        class_id=class_id,
        attendance_date=attendance_date,
    )


@router.get(
    "/attendance/analytics",
    response_model=AttendanceAnalyticsResponse,
)
async def attendance_analytics(
    session_id: UUID,
    term_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await attendance_service.get_analytics(
        db=db,
        school_id=user.school_id,
        session_id=session_id,
        term_id=term_id,
    )


# =====================================================
# 🏫 CLASSES MANAGEMENT
# =====================================================


@router.post("/classes")
async def create_class(
    payload: CreateClassRequest,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    if not user.school_id:
        raise HTTPException(
            status_code=400,
            detail="No school assigned",
        )

    return await school_class_service.create_class(
        db,
        payload,
        user.school_id,
    )


@router.get("/classes")
async def get_classes(
    db: DBSession,
    user: CurrentUser,
):
    return await school_class_service.get_classes(
        db,
        user.school_id,
    )


@router.get("/classes/{class_id}/dashboard")
async def class_dashboard(
    class_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_class_service.get_class_dashboard(
        db=db,
        class_id=class_id,
        school_id=user.school_id,
    )


@router.delete("/classes/{class_id}")
async def delete_class(
    class_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    return await school_class_service.delete_class(
        db,
        class_id,
    )


# =====================================================
# 👨‍🎓 SCHOOL STUDENTS
# =====================================================


@router.get("/students")
async def get_school_students(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await school_assignment_service.get_school_students(
        db,
        str(current_user.school_id),
    )


@router.get("/classes/{class_id}/available-students")
async def get_available_students(
    class_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_assignment_service.get_students_not_in_class(
        db=db,
        school_id=user.school_id,
        class_id=class_id,
    )


@router.get("/classes/{class_id}/students")
async def class_students(
    class_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_assignment_service.get_class_students(
        db=db,
        class_id=class_id,
        school_id=user.school_id,
    )


@router.post("/classes/{class_id}/assign-student/{student_id}")
async def assign_student(
    class_id: UUID,
    student_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_assignment_service.assign_student(
        db=db,
        student_id=student_id,
        class_id=class_id,
        school_id=user.school_id,
    )


@router.delete("/classes/{class_id}/students/{student_id}")
async def remove_student(
    class_id: UUID,
    student_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    result = await school_assignment_service.remove_student_from_class(
        db=db,
        student_id=student_id,
        class_id=class_id,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail="Student not found in class",
        )

    return {
        "message": "Student removed from class",
    }


# =====================================================
# 👨‍🏫 SCHOOL TEACHERS
# =====================================================


@router.get("/teachers")
async def get_school_teachers(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await school_assignment_service.get_school_teachers(
        db,
        str(current_user.school_id),
    )


@router.get("/classes/{class_id}/available-teachers")
async def available_teachers(
    class_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_assignment_service.get_teachers_not_in_class(
        db=db,
        school_id=user.school_id,
        class_id=class_id,
    )


@router.get("/classes/{class_id}/teachers")
async def class_teachers(
    class_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    return await school_assignment_service.get_class_teachers(
        db,
        class_id,
    )


# =====================================================
# 📚 TEACHER SUBJECT ASSIGNMENTS
# =====================================================


@router.post("/classes/{class_id}/assign-teacher/{teacher_id}")
async def assign_teacher_to_class(
    class_id: UUID,
    teacher_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_assignment_service.assign_teacher_to_class(
        db=db,
        teacher_id=teacher_id,
        class_id=class_id,
        school_id=user.school_id,
    )


@router.delete("/classes/{class_id}/teachers/{teacher_id}")
async def remove_teacher_from_class(
    class_id: UUID,
    teacher_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_assignment_service.remove_teacher_from_class(
        db=db,
        teacher_id=teacher_id,
        class_id=class_id,
    )


@router.post("/classes/{class_id}/subjects/{subject_id}/assign-teacher/{teacher_id}")
async def assign_teacher(
    class_id: UUID,
    subject_id: UUID,
    teacher_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_assignment_service.assign_teacher(
        db=db,
        teacher_id=teacher_id,
        class_id=class_id,
        subject_id=subject_id,
        school_id=user.school_id,
    )


@router.delete("/classes/{class_id}/subjects/{subject_id}/teachers/{teacher_id}")
async def remove_teacher_assignment(
    class_id: UUID,
    subject_id: UUID,
    teacher_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    deleted = await school_assignment_service.remove_teacher_assignment(
        db=db,
        teacher_id=teacher_id,
        class_id=class_id,
        subject_id=subject_id,
    )

    if not deleted["success"]:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found",
        )

    return {
        "message": "Teacher assignment removed",
    }


# =====================================================
# 📖 CLASS SUBJECT ASSIGNMENTS
# =====================================================


@router.get("/classes/{class_id}/assignments")
async def get_class_assignments(
    class_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    return await school_assignment_service.get_class_assignments(
        db,
        class_id,
    )


# =====================================================
# ⬆️ CLASS PROMOTION
# =====================================================


@router.post("/classes/promote")
async def promote_students(
    payload: PromoteStudentsRequest,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    return await school_assignment_service.promote_students(
        db=db,
        from_class_id=payload.from_class_id,
        to_class_id=payload.to_class_id,
        from_session_id=payload.from_session_id,
        to_session_id=payload.to_session_id,
    )


@router.get("/dashboard")
async def school_admin_dashboard(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: RequireSchoolAdmin,
):
    return await school_admin_dashboard_service.dashboard(
        db=db,
        current_user=current_user,
    )


@router.put("/students/{student_id}")
async def update_student(
    student_id: UUID,
    payload: UpdateStudentRequest,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_admin_service.update_student(
        db,
        user.school_id,
        student_id,
        payload,
    )


@router.put("/teachers/{teacher_id}")
async def update_teacher(
    teacher_id: UUID,
    payload: UpdateTeacherRequest,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_admin_service.update_teacher(
        db,
        user.school_id,
        teacher_id,
        payload,
    )


@router.put("/classes/{class_id}")
async def update_class(
    class_id: UUID,
    payload: UpdateClassRequest,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_admin_service.update_class(
        db,
        user.school_id,
        class_id,
        payload,
    )


@router.put("/subjects/{subject_id}")
async def update_subject(
    subject_id: UUID,
    payload: UpdateSubjectRequest,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_admin_service.update_subject(
        db,
        user.school_id,
        subject_id,
        payload,
    )


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_admin_service.delete_subject(
        db,
        user.school_id,
        subject_id,
    )


@router.get("/results/export")
async def export_results(
    session_id: UUID,
    term_id: UUID,
    class_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_admin_service.export_results(
        db,
        user.school_id,
        session_id,
        term_id,
        class_id,
    )


@router.get("/attendance/export")
async def export_attendance(
    session_id: UUID,
    term_id: UUID,
    db: DBSession,
    user: RequireSchoolAdmin,
):
    return await school_admin_service.export_attendance(
        db,
        user.school_id,
        session_id,
        term_id,
    )
