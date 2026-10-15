from uuid import UUID
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance.expense import Expense
from app.models.finance.expense_category import ExpenseCategory
from app.models.finance.operations import FinanceAccount
from app.repositories.finance.expenses import expense_repository, expense_category_repository
from app.services.finance.common import money, get_school_row, ensure_default_accounts, require_account, post_journal

class ExpenseService:
    async def list_categories(self, db, school_id):
        return await expense_category_repository.list(db, school_id, limit=500)
    async def create_category(self, db: AsyncSession, school_id: UUID, name: str):
        name = name.strip()
        exists = (await db.execute(select(ExpenseCategory).where(ExpenseCategory.school_id == school_id, ExpenseCategory.name.ilike(name)))).scalar_one_or_none()
        if exists: raise HTTPException(409, "Expense category already exists.")
        return await expense_category_repository.add(db, ExpenseCategory(school_id=school_id, name=name, is_active=True))
    async def create(self, db: AsyncSession, school_id: UUID, user, payload):
        category = await get_school_row(db, ExpenseCategory, school_id, payload.category_id, "Expense category")
        if not category.is_active: raise HTTPException(400, "Expense category is inactive.")
        await ensure_default_accounts(db, school_id)
        payment_account = await require_account(db, school_id, payload.payment_account_id, {"ASSET"})
        # Keep the admin workflow simple: default to the standard operating-expense
        # account unless an internal caller explicitly supplies another expense account.
        if payload.expense_account_id:
            expense_account = await require_account(db, school_id, payload.expense_account_id, {"EXPENSE"})
        else:
            expense_account = (await db.execute(select(FinanceAccount).where(
                FinanceAccount.school_id == school_id,
                FinanceAccount.code == "5000",
                FinanceAccount.account_type == "EXPENSE",
                FinanceAccount.is_active.is_(True),
            ))).scalar_one_or_none()
            if expense_account is None:
                raise HTTPException(500, "Default expense account could not be initialized. Please try again.")
        row = Expense(school_id=school_id, category_id=category.id, amount=money(payload.amount), payment_method=payload.payment_method, expense_date=payload.expense_date, description=payload.description, reference=payload.reference)
        await expense_repository.add(db, row)
        await post_journal(db, school_id, user.id, f"EXP-{row.id.hex[:12].upper()}", payload.expense_date, "EXPENSE", row.id, payload.description[:255], [(expense_account.id, payload.description[:255], row.amount, 0), (payment_account.id, "Expense disbursement", 0, row.amount)])
        return row
    async def list(self, db: AsyncSession, school_id: UUID, category_id=None, from_date=None, to_date=None, limit=100, offset=0):
        stmt = select(Expense).where(Expense.school_id == school_id)
        if category_id: stmt = stmt.where(Expense.category_id == category_id)
        if from_date: stmt = stmt.where(Expense.expense_date >= from_date)
        if to_date: stmt = stmt.where(Expense.expense_date <= to_date)
        return (await db.execute(stmt.order_by(Expense.expense_date.desc()).limit(limit).offset(offset))).scalars().all()

expense_service = ExpenseService()
