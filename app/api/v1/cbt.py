from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import DBSession, RequireSchoolAdmin, RequireStudent
from app.schemas.cbt import (
    CBTExamCreate,
    QuestionCreate,
    SubmitAnswerRequest,
)
from app.services.cbt_service import CBTService

router = APIRouter(
    prefix="/cbt",
    tags=["Computer Based Test"],
)

service = CBTService()

# ==========================================================
# SCHOOL ADMIN ENDPOINTS
# ==========================================================


@router.post("/admin/exams")
async def create_exam(
    payload: CBTExamCreate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.create_exam(
        db=db,
        school_id=current_user.school_id,
        user=current_user,
        payload=payload,
    )


@router.put("/admin/exams/{exam_id}")
async def update_exam(
    exam_id: UUID,
    payload: CBTExamCreate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.update_exam(
        db=db,
        exam_id=exam_id,
        school_id=current_user.school_id,
        payload=payload,
    )


@router.post("/admin/exams/{exam_id}/questions")
async def add_question(
    exam_id: UUID,
    payload: QuestionCreate,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    try:
        return await service.add_question(
            db=db,
            exam_id=exam_id,
            payload=payload,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.patch("/admin/exams/{exam_id}/publish")
async def publish_exam(
    exam_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    try:
        return await service.publish_exam(
            db=db,
            exam_id=exam_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get("/admin/exams")
async def get_school_exams(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    try:
        return await service.get_school_exams(
            db=db,
            school_id=current_user.school_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get("/admin/exams/{exam_id}")
async def get_exam_details(
    exam_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    try:
        return await service.get_exam_details(
            db=db,
            exam_id=exam_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.put("/admin/questions/{question_id}")
async def update_question(
    question_id: UUID,
    payload: QuestionCreate,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    return await service.update_question(
        db=db,
        question_id=question_id,
        payload=payload,
    )


@router.delete("/admin/questions/{question_id}")
async def delete_question(
    question_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    try:
        return await service.delete_question(
            db=db,
            question_id=question_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.delete("/admin/exams/{exam_id}")
async def delete_exam(
    exam_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    try:
        return await service.delete_exam(
            db=db,
            exam_id=exam_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get("/admin/exams/{exam_id}/results")
async def get_exam_results(
    exam_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    try:
        return await service.get_exam_results(
            db=db,
            exam_id=exam_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get("/admin/attempts/{attempt_id}")
async def get_attempt(
    attempt_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
):
    try:
        return await service.get_attempt(
            db=db,
            attempt_id=attempt_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# ==========================================================
# STUDENT ENDPOINTS
# ==========================================================


@router.get("/student/exams")
async def available_exams(
    class_id: UUID,
    db: DBSession,
    _: RequireStudent,
):
    try:
        return await service.get_available_exams(
            db=db,
            class_id=class_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/student/exams/{exam_id}/start")
async def start_exam(
    exam_id: UUID,
    db: DBSession,
    current_user: RequireStudent,
):
    try:
        return await service.start_exam(
            db=db,
            exam_id=exam_id,
            student_id=current_user.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/student/answers")
async def submit_answer(
    payload: SubmitAnswerRequest,
    db: DBSession,
    _: RequireStudent,
):
    try:
        return await service.submit_answer(
            db=db,
            payload=payload,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/student/attempts/{attempt_id}/submit")
async def submit_exam(
    attempt_id: UUID,
    db: DBSession,
    _: RequireStudent,
):
    try:
        return await service.submit_exam(
            db=db,
            attempt_id=attempt_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get("/student/attempts/{attempt_id}")
async def resume_exam(
    attempt_id: UUID,
    db: DBSession,
    current_user: RequireStudent,
):
    try:
        return await service.resume_exam(
            db=db,
            attempt_id=attempt_id,
            student_id=current_user.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get("/student/results/{attempt_id}")
async def student_result(
    attempt_id: UUID,
    db: DBSession,
    current_user: RequireStudent,
):
    try:
        return await service.get_student_result(
            db=db,
            attempt_id=attempt_id,
            student_id=current_user.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get("/student/history")
async def student_history(
    db: DBSession,
    current_user: RequireStudent,
):
    try:
        return await service.get_student_history(
            db=db,
            student_id=current_user.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
