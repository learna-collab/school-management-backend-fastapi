from fastapi import APIRouter
from uuid import UUID
from app.core.deps import DBSession, RequireSchoolAdmin
from app.schemas.finance.fees import FeeCategoryCreate, StudentFeeCreate, BulkStudentFeeCreate
from app.services.finance.common import require_school
from app.services.finance.fees import fee_service

router = APIRouter()
@router.get("/fee-categories")
async def list_fee_categories(db: DBSession, user: RequireSchoolAdmin):
    return await fee_service.list_categories(db, require_school(user))
@router.post("/fee-categories", status_code=201)
async def create_fee_category(payload: FeeCategoryCreate, db: DBSession, user: RequireSchoolAdmin):
    return await fee_service.create_category(db, require_school(user), payload.name, payload.description)
@router.post("/student-fees", status_code=201)
async def assign_student_fee(payload: StudentFeeCreate, db: DBSession, user: RequireSchoolAdmin):
    return await fee_service.assign_student_fee(db, require_school(user), payload)
@router.post("/fee-schedules/apply", status_code=201)
async def apply_fee_schedule(payload: BulkStudentFeeCreate, db: DBSession, user: RequireSchoolAdmin):
    """Apply one fee to every enrolled student or every student in one class."""
    return await fee_service.assign_fee_to_students(db, require_school(user), user, payload)
@router.get("/student-fees")
async def list_student_fees(db: DBSession, user: RequireSchoolAdmin, student_id: UUID | None = None, session_id: UUID | None = None, term_id: UUID | None = None):
    return await fee_service.list_student_fees(db, require_school(user), student_id, session_id, term_id)
