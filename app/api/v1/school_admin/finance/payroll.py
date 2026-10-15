from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from app.core.deps import DBSession, RequireSchoolAdmin
from app.models.finance.operations import FinanceSalaryProfile, PayrollRecord
from app.models.user import User
from app.schemas.finance.payroll import PayrollCreate, PayrollPayRequest, SalaryProfileCreate
from app.services.finance.common import require_school, get_school_row
from app.services.finance.payroll import payroll_service
router=APIRouter()
def payroll_out(row):
    return {"id":row.id,"employee_user_id":row.employee_user_id,"pay_year":row.pay_year,"pay_month":row.pay_month,"basic_salary":row.basic_salary,"allowances":row.allowances,"deductions":row.deductions,"net_pay":row.net_pay,"status":row.status,"payment_date":row.payment_date,"payment_method":row.payment_method,"reference":row.reference,"note":row.note}
@router.post("/salary-profiles", status_code=201)
async def create_salary_profile(payload: SalaryProfileCreate, db: DBSession, user: RequireSchoolAdmin): return await payroll_service.create_profile(db, require_school(user), payload)
@router.get("/salary-profiles")
async def list_salary_profiles(db: DBSession, user: RequireSchoolAdmin): return await payroll_service.list_profiles(db, require_school(user))
@router.post("/payroll/generate", status_code=201)
async def generate_payroll(payload: PayrollCreate, db: DBSession, user: RequireSchoolAdmin): return payroll_out(await payroll_service.generate(db, require_school(user), user, payload))
@router.post("/payroll/generate-from-profile", status_code=201)
async def generate_from_profile(employee_user_id: UUID, pay_year: int, pay_month: int, db: DBSession, user: RequireSchoolAdmin):
    school_id=require_school(user)
    profile=(await db.execute(select(FinanceSalaryProfile).where(FinanceSalaryProfile.school_id==school_id, FinanceSalaryProfile.employee_user_id==employee_user_id, FinanceSalaryProfile.is_active.is_(True)))).scalar_one_or_none()
    if not profile: raise HTTPException(404,"Active salary profile not found.")
    payload=PayrollCreate(employee_user_id=employee_user_id,pay_year=pay_year,pay_month=pay_month,basic_salary=profile.basic_salary,allowances=profile.default_allowances,deductions=profile.default_deductions,note=profile.note)
    return payroll_out(await payroll_service.generate(db, school_id, user, payload))
@router.get("/payroll")
async def list_payroll(db: DBSession, user: RequireSchoolAdmin, pay_year: int | None = None, pay_month: int | None = None, payroll_status: str | None = None, employee_user_id: UUID | None = None):
    rows=await payroll_service.list(db,require_school(user),pay_year,pay_month,payroll_status,employee_user_id)
    return [payroll_out(x) for x in rows]
@router.post("/payroll/{payroll_id}/pay")
async def pay_payroll(payroll_id: UUID, payload: PayrollPayRequest, db: DBSession, user: RequireSchoolAdmin): return payroll_out(await payroll_service.pay(db,require_school(user),user,payroll_id,payload))
@router.get("/payroll/{payroll_id}/payslip")
async def payslip(payroll_id: UUID, db: DBSession, user: RequireSchoolAdmin):
    school_id=require_school(user); row=await get_school_row(db,PayrollRecord,school_id,payroll_id,"Payroll record"); employee=await get_school_row(db,User,school_id,row.employee_user_id,"Employee")
    return {**payroll_out(row),"employee":{"id":employee.id,"first_name":employee.first_name,"last_name":employee.last_name,"email":employee.email,"role":employee.role.value},"school_id":school_id,"generated_at":row.updated_at}
