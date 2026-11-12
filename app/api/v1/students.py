from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.deps import (
    DBSession,
    RequireStudent,
    RequireStudentOrSchoolAdmin,
)
from app.schemas.learning_centre import (
    StudentLearningProgressUpdate,
    StudentPracticeAnswerRequest,
)
from app.schemas.result_responses import (
    StudentResultApiResponse,
    StudentResultResponse,
)
from app.services.attendance_service import attendance_service
from app.services.dashboard_services import (
    dashboard_service,
)
from app.services.report_card_service import report_card_service
from app.services.result_service import result_service
from app.services.school_class_service import school_class_service
from app.services.student_learning_centre_service import (
    student_learning_centre_service,
)

router = APIRouter(
    prefix="/student",
    tags=["Student Endpoints"],
)


# =====================================================
# CLASSES
# =====================================================


@router.get("/classes")
async def get_classes(
    db: DBSession,
    user: RequireStudentOrSchoolAdmin,
):
    return await school_class_service.get_classes(
        db=db,
        school_id=user.school_id,
    )


# =====================================================
# RESULTS
# =====================================================


@router.get(
    "/results",
    response_model=StudentResultApiResponse,
)
async def get_results(
    session_id: UUID,
    term_id: UUID,
    db: DBSession,
    user: RequireStudent,
):
    print(session_id)
    print(term_id)
    print(user.id)
    return await result_service.get_student_result(
        db=db,
        student=user,
        session_id=session_id,
        term_id=term_id,
    )


@router.get("/results/download")
async def download_report_card(
    session_id: UUID,
    term_id: UUID,
    db: DBSession,
    user: RequireStudent,
):
    result = await result_service.get_student_result_for_pdf(
        db=db,
        student=user,
        session_id=session_id,
        term_id=term_id,
    )

    attendance = await attendance_service.get_student_attendance(
        db=db,
        student=user,
        session_id=session_id,
        term_id=term_id,
    )

    pdf = report_card_service.generate(
        student=user,
        result=result,
        attendance=attendance,
    )

    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report_card.pdf"},
    )


# =====================================================
# ATTENDANCE
# =====================================================


@router.get("/attendance")
async def get_attendance(
    session_id: UUID,
    term_id: UUID,
    db: DBSession,
    user: RequireStudent,
):
    return await attendance_service.get_student_attendance(
        db=db,
        student=user,
        session_id=session_id,
        term_id=term_id,
    )


@router.get("/attendance/summary")
async def get_attendance_summary(
    session_id: UUID,
    term_id: UUID,
    db: DBSession,
    user: RequireStudent,
):
    return await attendance_service.get_student_term_summary(
        db=db,
        student=user,
        session_id=session_id,
        term_id=term_id,
    )


# =====================================================
# STUDENT LEARNING CENTRE
# =====================================================


@router.get("/learning-centre")
async def get_student_learning_centre(
    db: DBSession,
    user: RequireStudent,
    week_number: int | None = None,
):
    return await student_learning_centre_service.get_learning_centre(
        db=db,
        user=user,
        week_number=week_number,
    )


@router.get("/learning-centre/{content_id}")
async def get_student_learning_content(
    content_id: UUID,
    db: DBSession,
    user: RequireStudent,
):
    return await student_learning_centre_service.get_lesson_content(
        db=db,
        user=user,
        content_id=content_id,
    )


@router.patch("/learning-centre/{content_id}/progress")
async def update_student_learning_progress(
    content_id: UUID,
    payload: StudentLearningProgressUpdate,
    db: DBSession,
    user: RequireStudent,
):
    return await student_learning_centre_service.update_progress(
        db=db,
        user=user,
        content_id=content_id,
        completed_sections=payload.completed_sections,
        completed_activities=payload.completed_activities,
    )


@router.post("/learning-centre/{content_id}/practice/{question_id}/answer")
async def submit_student_practice_answer(
    content_id: UUID,
    question_id: str,
    payload: StudentPracticeAnswerRequest,
    db: DBSession,
    user: RequireStudent,
):
    return await student_learning_centre_service.submit_practice_answer(
        db=db,
        user=user,
        content_id=content_id,
        question_id=question_id,
        answer=payload.answer,
    )


@router.get("/learning-centre/{content_id}/progress")
async def get_student_lesson_progress(
    content_id: UUID,
    db: DBSession,
    user: RequireStudent,
):
    return await student_learning_centre_service.get_lesson_progress(
        db=db,
        user=user,
        content_id=content_id,
    )


@router.get("/dashboard")
async def student_dashboard(
    db: DBSession,
    user: RequireStudent,
):
    return await dashboard_service.student_dashboard(
        db=db,
        user=user,
    )
