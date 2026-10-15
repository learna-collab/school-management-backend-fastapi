from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.finance.operations import FinanceSalaryProfile, PayrollRecord, FinanceAccount
from app.repositories.finance.payroll import salary_profile_repository, payroll_repository
from app.services.finance.common import money, get_school_row, ensure_default_accounts, require_account, post_journal

class PayrollService:
    async def create_profile(self, db: AsyncSession, school_id: UUID, payload):
        employee = await get_school_row(db, User, school_id, payload.employee_user_id, "Employee")
        if employee.role.value not in {"TEACHER", "SCHOOL_ADMIN"}: raise HTTPException(400, "Payroll recipient must be an existing school staff user.")
        row = (await db.execute(select(FinanceSalaryProfile).where(FinanceSalaryProfile.school_id == school_id, FinanceSalaryProfile.employee_user_id == employee.id))).scalar_one_or_none()
        if row:
            row.basic_salary = money(payload.basic_salary); row.default_allowances = money(payload.default_allowances); row.default_deductions = money(payload.default_deductions); row.note = payload.note; row.is_active = True
            await db.flush(); return row
        return await salary_profile_repository.add(db, FinanceSalaryProfile(school_id=school_id, employee_user_id=employee.id, basic_salary=money(payload.basic_salary), default_allowances=money(payload.default_allowances), default_deductions=money(payload.default_deductions), note=payload.note, is_active=True))
    async def list_profiles(self, db, school_id):
        return await salary_profile_repository.list(db, school_id, limit=500)
    async def generate(self, db: AsyncSession, school_id: UUID, user: User, payload):
        employee = await get_school_row(db, User, school_id, payload.employee_user_id, "Employee")
        if employee.role.value not in {"TEACHER", "SCHOOL_ADMIN"}: raise HTTPException(400, "Payroll recipient must be an existing school staff user.")
        exists = (await db.execute(select(PayrollRecord).where(PayrollRecord.school_id == school_id, PayrollRecord.employee_user_id == employee.id, PayrollRecord.pay_year == payload.pay_year, PayrollRecord.pay_month == payload.pay_month))).scalar_one_or_none()
        if exists: raise HTTPException(409, "Payroll already exists for this employee and period.")
        net = money(payload.basic_salary + payload.allowances - payload.deductions)
        if net < 0: raise HTTPException(400, "Deductions cannot exceed salary plus allowances.")
        return await payroll_repository.add(db, PayrollRecord(school_id=school_id, employee_user_id=employee.id, pay_year=payload.pay_year, pay_month=payload.pay_month, basic_salary=money(payload.basic_salary), allowances=money(payload.allowances), deductions=money(payload.deductions), net_pay=net, status="DRAFT", note=payload.note, created_by=user.id))
    async def list(self, db, school_id, pay_year=None, pay_month=None, status=None, employee_user_id=None):
        stmt = select(PayrollRecord).where(PayrollRecord.school_id == school_id)
        for field, value in (("pay_year", pay_year), ("pay_month", pay_month), ("status", status.upper() if status else None), ("employee_user_id", employee_user_id)):
            if value is not None: stmt = stmt.where(getattr(PayrollRecord, field) == value)
        return (await db.execute(stmt.order_by(PayrollRecord.pay_year.desc(), PayrollRecord.pay_month.desc()))).scalars().all()
    async def pay(self, db: AsyncSession, school_id: UUID, user: User, payroll_id: UUID, payload):
        await ensure_default_accounts(db, school_id)
        row = await get_school_row(db, PayrollRecord, school_id, payroll_id, "Payroll record")
        if row.status == "PAID": raise HTTPException(409, "Payroll has already been paid.")
        account = await require_account(db, school_id, payload.payment_account_id, {"ASSET"})
        salary_expense = (await db.execute(select(FinanceAccount).where(FinanceAccount.school_id == school_id, FinanceAccount.code == "5100"))).scalar_one()
        entry = await post_journal(db, school_id, user.id, f"PAY-{row.id.hex[:12].upper()}", payload.payment_date, "PAYROLL", row.id, f"Payroll {row.pay_month:02d}/{row.pay_year}", [(salary_expense.id, "Staff salaries", row.net_pay, 0), (account.id, "Salary disbursement", 0, row.net_pay)])
        row.status = "PAID"; row.payment_date = payload.payment_date; row.payment_method = payload.payment_method; row.reference = payload.reference; row.payment_account_id = account.id; row.journal_entry_id = entry.id
        await db.flush(); return row

payroll_service = PayrollService()
