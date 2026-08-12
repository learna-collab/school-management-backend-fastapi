from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import DBSession, RequireSchoolAdmin, get_db
from app.services.cbt_batch_upload_service import cbt_batch_upload_service

router = APIRouter(prefix="/cbt/admin", tags=["CBT Admin"])

upload_file = File(...)


@router.post("/exams/{exam_id}/questions/batch-upload")
async def batch_upload_questions(
    exam_id: UUID,
    db: DBSession,
    _: RequireSchoolAdmin,
    file: UploadFile = upload_file,
):
    return await cbt_batch_upload_service.upload_questions(
        db=db,
        exam_id=exam_id,
        file=file,
    )
