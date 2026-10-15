from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.finance.operations import FinanceAccount, FinanceJournalEntry, FinanceJournalLine

CENT = Decimal("0.01")
def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT)

def require_school(user: User) -> UUID:
    if not user.school_id:
        raise HTTPException(status_code=403, detail="Your account is not associated with a school.")
    return user.school_id

async def get_school_row(db: AsyncSession, model, school_id: UUID, row_id: UUID, label: str = "Record"):
    result = await db.execute(select(model).where(model.id == row_id, model.school_id == school_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{label} not found in this school.")
    return row

async def ensure_default_accounts(db: AsyncSession, school_id: UUID):
    defaults = [("1000", "Cash on Hand", "ASSET"), ("1010", "Bank Account", "ASSET"), ("1100", "Accounts Receivable", "ASSET"), ("4000", "School Fees Revenue", "REVENUE"), ("5000", "General Operating Expenses", "EXPENSE"), ("5100", "Staff Salaries Expense", "EXPENSE")]
    codes = [item[0] for item in defaults]
    result = await db.execute(select(FinanceAccount.code).where(FinanceAccount.school_id == school_id, FinanceAccount.code.in_(codes)))
    existing_codes = set(result.scalars().all())
    for code, name, kind in defaults:
        if code not in existing_codes:
            db.add(FinanceAccount(school_id=school_id, code=code, name=name, account_type=kind, is_active=True, is_system=True))
    await db.flush()

async def require_account(db: AsyncSession, school_id: UUID, account_id: UUID, types: set[str]):
    account = await get_school_row(db, FinanceAccount, school_id, account_id, "Account")
    if not account.is_active or account.account_type not in types:
        raise HTTPException(status_code=400, detail=f"Account must be active and have type: {', '.join(sorted(types))}.")
    return account

async def post_journal(db: AsyncSession, school_id: UUID, user_id: UUID, number: str, entry_date, source_type: str, source_id: UUID, description: str, lines: list[tuple[UUID, str, Decimal, Decimal]]):
    debit = money(sum((money(line[2]) for line in lines), Decimal("0")))
    credit = money(sum((money(line[3]) for line in lines), Decimal("0")))
    if debit <= 0 or debit != credit:
        raise HTTPException(status_code=400, detail="Journal entry must balance with positive debit and credit totals.")
    entry = FinanceJournalEntry(school_id=school_id, entry_number=number, entry_date=entry_date, source_type=source_type, source_id=source_id, description=description, status="POSTED", posted_by=user_id)
    db.add(entry); await db.flush()
    for account_id, line_description, line_debit, line_credit in lines:
        await get_school_row(db, FinanceAccount, school_id, account_id, "Ledger account")
        db.add(FinanceJournalLine(school_id=school_id, entry_id=entry.id, account_id=account_id, description=line_description, debit=money(line_debit), credit=money(line_credit)))
    await db.flush()
    return entry
