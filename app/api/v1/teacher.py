from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.deps import (
    DBSession,
    RequireTeacher,
)
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceSubmissionResponse,
)
from app.schemas.result_responses import (
    ClassResultResponse,
    ResultSubmissionResponse,
)
from app.schemas.result_schema import (
    ResultBatchCreate,
    ResultStatusResponse,
    UpdateResultRecord,
    UpdateTeacherComment,
)
from app.services.attendance_service import attendance_service
from app.services.dashboard_services import (
    dashboard_service,
)
from app.services.lesson_service import lesson_service
from app.services.result_service import result_service
from app.services.teacher_service import teacher_service

router = APIRouter(
    prefix="/teacher",
    tags=["Teacher Endpoints"],
)


# =====================================================
# LESSONS
# =====================================================


@router.get("/lessons/search")
async def search_lessons(
    class_name: str,
    subject_name: str,
    session_name: str,
    term_name: str,
    db: DBSession,
    _: RequireTeacher,
):
    return await lesson_service.get_lessons_filtered(
        db=db,
        class_name=class_name,
        subject_name=subject_name,
        session_name=session_name,
        term_name=term_name,
    )


# =====================================================
# ATTENDANCE
# =====================================================


@router.post(
    "/attendance",
    response_model=AttendanceSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_attendance(
    payload: AttendanceCreate,
    db: DBSession,
    user: RequireTeacher,
):
    return await attendance_service.submit_attendance(
        db=db,
        payload=payload,
        teacher=user,
    )


@router.get("/attendance/class")
async def get_class_attendance(
    class_id: UUID,
    attendance_date: date,
    db: DBSession,
    user: RequireTeacher,
):
    return await attendance_service.get_class_attendance(
        db=db,
        teacher=user,
        class_id=class_id,
        attendance_date=attendance_date,
    )


# =====================================================
# RESULTS
# =====================================================


@router.get(
    "/results/{class_id}/editable",
)
async def get_editable_results(
    class_id: UUID,
    db: DBSession,
    teacher: RequireTeacher,
):
    return await result_service.get_editable_batch(
        db,
        teacher,
        class_id,
    )


@router.post(
    "/results/{batch_id}/resubmit",
)
async def resubmit_results(
    batch_id: UUID,
    db: DBSession,
    teacher: RequireTeacher,
):
    return await result_service.resubmit_batch(
        db,
        batch_id,
        teacher,
    )


@router.get(
    "/results/status",
    response_model=ResultStatusResponse,
)
async def get_result_status(
    class_id: UUID,
    db: DBSession,
    teacher: RequireTeacher,
):
    return await result_service.get_result_status(
        db=db,
        teacher=teacher,
        class_id=class_id,
    )


@router.post(
    "/results/draft",
    response_model=ResultSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_result_draft(
    payload: ResultBatchCreate,
    db: DBSession,
    user: RequireTeacher,
):
    return await result_service.save_draft(
        db=db,
        payload=payload,
        teacher=user,
    )


@router.post(
    "/results/submit",
    response_model=ResultSubmissionResponse,
)
async def submit_results(
    payload: ResultBatchCreate,
    db: DBSession,
    user: RequireTeacher,
):
    return await result_service.submit_results(
        db=db,
        payload=payload,
        teacher=user,
    )


@router.put(
    "/results/{batch_id}",
    response_model=ResultSubmissionResponse,
)
async def update_results(
    batch_id: UUID,
    payload: ResultBatchCreate,
    db: DBSession,
    user: RequireTeacher,
):
    return await result_service.update_results(
        db=db,
        batch_id=batch_id,
        payload=payload,
        teacher=user,
    )


@router.get(
    "/results/class",
    response_model=ClassResultResponse,
)
async def get_class_results(
    class_id: UUID,
    session_id: UUID | None,
    term_id: UUID | None,
    db: DBSession,
    user: RequireTeacher,
):
    return await result_service.get_class_results(
        db=db,
        school_id=user.school_id,
        class_id=class_id,
        session_id=session_id,
        term_id=term_id,
    )


@router.get(
    "/results/{batch_id}",
)
async def get_batch(
    batch_id: UUID,
    db: DBSession,
    user: RequireTeacher,
):
    return await result_service.get_batch(
        db=db,
        batch_id=batch_id,
        teacher=user,
    )


@router.get(
    "/results/{batch_id}/view",
    response_model=ClassResultResponse,
)
async def view_batch(
    batch_id: UUID,
    db: DBSession,
    user: RequireTeacher,
):
    return await result_service.view_batch(
        db=db,
        batch_id=batch_id,
        teacher=user,
    )


@router.get(
    "/results/class/{class_id}/batches",
)
async def get_class_batches(
    class_id: UUID,
    db: DBSession,
    user: RequireTeacher,
):
    return await result_service.get_class_batches(
        db=db,
        class_id=class_id,
        school_id=user.school_id,
    )


@router.patch(
    "/results/records/{record_id}",
)
async def update_result_record(
    record_id: UUID,
    payload: UpdateResultRecord,
    db: DBSession,
    user: RequireTeacher,
):
    return await result_service.update_result_record(
        db=db,
        record_id=record_id,
        payload=payload,
        user=user,
    )


@router.patch(
    "/results/records/{record_id}/comment",
)
async def update_teacher_comment(
    record_id: UUID,
    payload: UpdateTeacherComment,
    db: DBSession,
    user: RequireTeacher,
):
    return await result_service.update_teacher_comment(
        db=db,
        record_id=record_id,
        comment=payload.teacher_comment,
    )


@router.get("/dashboard")
async def teacher_dashboard(
    db: DBSession,
    user: RequireTeacher,
):
    return await dashboard_service.teacher_dashboard(
        db=db,
        user=user,
    )


@router.get("/classes")
async def get_teacher_classes(
    db: DBSession,
    current_user: RequireTeacher,
):
    classes = await dashboard_service.get_classes(
        db,
        current_user,
    )

    return {
        "classes": classes,
    }


@router.get("/students")
async def get_students(
    db: DBSession,
    teacher: RequireTeacher,
    class_id: str = Query(...),
):
    students = await teacher_service.get_class_students(
        db, teacher, class_id, teacher.school_id
    )

    return {
        "students": students,
    }


@router.get("/subjects")
async def get_subjects(
    db: DBSession,
    current_user: RequireTeacher,
    class_id: str = Query(...),
):
    subjects = await teacher_service.get_subjects(
        db,
        current_user,
        class_id,
    )

    return {
        "subjects": subjects,
    }
