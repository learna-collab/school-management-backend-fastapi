from datetime import date
from uuid import UUID
from fastapi import APIRouter, Query, HTTPException
from app.core.deps import DBSession, RequireSchoolAdmin
from app.schemas.finance.accounting import FinanceAccountCreate
from app.services.finance.common import require_school
from app.services.finance.accounting import accounting_service
router=APIRouter()
@router.post("/accounts/initialize",status_code=201)
async def initialize_accounts(db: DBSession,user: RequireSchoolAdmin): return await accounting_service.initialize_accounts(db,require_school(user))
@router.get("/accounts")
async def list_accounts(db: DBSession,user: RequireSchoolAdmin): return await accounting_service.list_accounts(db,require_school(user))
@router.post("/accounts",status_code=201)
async def create_account(payload: FinanceAccountCreate,db: DBSession,user: RequireSchoolAdmin): return await accounting_service.create_account(db,require_school(user),payload)
@router.get("/ledger")
async def ledger(db: DBSession,user: RequireSchoolAdmin,from_date: date|None=None,to_date: date|None=None,account_id: UUID|None=None,limit:int=Query(200,ge=1,le=1000),offset:int=Query(0,ge=0)):
    if from_date and to_date and from_date>to_date: raise HTTPException(400,"from_date must be on or before to_date")
    return await accounting_service.ledger(db,require_school(user),from_date,to_date,account_id,limit,offset)
@router.get("/reports/trial-balance")
async def trial_balance(db: DBSession,user: RequireSchoolAdmin,as_of: date|None=None): return await accounting_service.trial_balance(db,require_school(user),as_of)
@router.get("/dashboard")
async def dashboard(db: DBSession,user: RequireSchoolAdmin,from_date: date|None=None,to_date: date|None=None):
    if from_date and to_date and from_date>to_date: raise HTTPException(400,"from_date must be on or before to_date")
    return await accounting_service.dashboard(db,require_school(user),from_date,to_date)

@router.get("/reports/reconciliation")
async def reconciliation(db: DBSession, user: RequireSchoolAdmin, from_date: date | None = None, to_date: date | None = None):
    if from_date and to_date and from_date > to_date: raise HTTPException(400, "from_date must be on or before to_date")
    return await accounting_service.reconciliation(db, require_school(user), from_date, to_date)
