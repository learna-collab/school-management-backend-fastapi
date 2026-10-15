from datetime import date
from uuid import UUID
from fastapi import APIRouter, Query
from app.core.deps import DBSession, RequireSchoolAdmin
from app.schemas.finance.expenses import ExpenseCategoryCreate, ExpenseCreate
from app.services.finance.common import require_school
from app.services.finance.expenses import expense_service
router=APIRouter()
@router.get("/expense-categories")
async def list_categories(db: DBSession, user: RequireSchoolAdmin): return await expense_service.list_categories(db, require_school(user))
@router.post("/expense-categories", status_code=201)
async def create_category(payload: ExpenseCategoryCreate, db: DBSession, user: RequireSchoolAdmin): return await expense_service.create_category(db, require_school(user), payload.name)
@router.post("/expenses", status_code=201)
async def create_expense(payload: ExpenseCreate, db: DBSession, user: RequireSchoolAdmin): return await expense_service.create(db, require_school(user), user, payload)
@router.get("/expenses")
async def list_expenses(db: DBSession, user: RequireSchoolAdmin, category_id: UUID | None = None, from_date: date | None = None, to_date: date | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return await expense_service.list(db, require_school(user), category_id, from_date, to_date, limit, offset)
