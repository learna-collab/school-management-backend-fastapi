from datetime import date
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance.operations import FinanceAccount, FinanceJournalEntry, FinanceJournalLine, FinanceInvoice, FinanceInvoicePayment, PayrollRecord
from app.models.finance.expense import Expense
from app.services.finance.common import money, ensure_default_accounts

class AccountingService:
    async def initialize_accounts(self, db, school_id):
        await ensure_default_accounts(db, school_id)
        return (await db.execute(select(FinanceAccount).where(FinanceAccount.school_id == school_id).order_by(FinanceAccount.code))).scalars().all()
    async def list_accounts(self, db, school_id):
        return (await db.execute(select(FinanceAccount).where(FinanceAccount.school_id == school_id).order_by(FinanceAccount.code))).scalars().all()
    async def create_account(self, db: AsyncSession, school_id: UUID, payload):
        exists = (await db.execute(select(FinanceAccount).where(FinanceAccount.school_id == school_id, FinanceAccount.code == payload.code.strip().upper()))).scalar_one_or_none()
        if exists: raise HTTPException(409, "An account with this code already exists.")
        row = FinanceAccount(school_id=school_id, code=payload.code.strip().upper(), name=payload.name.strip(), account_type=payload.account_type, description=payload.description, is_active=True, is_system=False)
        db.add(row); await db.flush(); return row
    async def ledger(self, db, school_id, from_date=None, to_date=None, account_id=None, limit=200, offset=0):
        stmt = select(FinanceJournalEntry).where(FinanceJournalEntry.school_id == school_id)
        if from_date: stmt = stmt.where(FinanceJournalEntry.entry_date >= from_date)
        if to_date: stmt = stmt.where(FinanceJournalEntry.entry_date <= to_date)
        if account_id: stmt = stmt.where(FinanceJournalEntry.id.in_(select(FinanceJournalLine.entry_id).where(FinanceJournalLine.school_id == school_id, FinanceJournalLine.account_id == account_id)))
        entries = (await db.execute(stmt.order_by(FinanceJournalEntry.entry_date.desc(), FinanceJournalEntry.created_at.desc()).limit(limit).offset(offset))).scalars().all()
        output=[]
        for entry in entries:
            lines = (await db.execute(select(FinanceJournalLine, FinanceAccount).join(FinanceAccount, FinanceAccount.id == FinanceJournalLine.account_id).where(FinanceJournalLine.entry_id == entry.id, FinanceJournalLine.school_id == school_id))).all()
            output.append({"entry": entry, "lines": [{"account_id": line.account_id, "account_code": account.code, "account_name": account.name, "description": line.description, "debit": line.debit, "credit": line.credit} for line, account in lines]})
        return output
    async def trial_balance(self, db, school_id, as_of=None):
        accounts = (await db.execute(select(FinanceAccount).where(FinanceAccount.school_id == school_id, FinanceAccount.is_active.is_(True)).order_by(FinanceAccount.code))).scalars().all()
        rows=[]; total_debit=Decimal("0.00"); total_credit=Decimal("0.00")
        for account in accounts:
            stmt = select(FinanceJournalLine).join(FinanceJournalEntry, FinanceJournalEntry.id == FinanceJournalLine.entry_id).where(FinanceJournalLine.school_id == school_id, FinanceJournalLine.account_id == account.id, FinanceJournalEntry.status == "POSTED")
            if as_of: stmt=stmt.where(FinanceJournalEntry.entry_date <= as_of)
            lines=(await db.execute(stmt)).scalars().all()
            debit=money(sum((x.debit for x in lines), Decimal("0"))); credit=money(sum((x.credit for x in lines), Decimal("0")))
            rows.append({"account_id":account.id,"code":account.code,"name":account.name,"account_type":account.account_type,"debit":debit,"credit":credit,"net_debit":money(debit-credit)})
            total_debit+=debit; total_credit+=credit
        return {"as_of":as_of,"accounts":rows,"total_debit":money(total_debit),"total_credit":money(total_credit),"balanced":money(total_debit)==money(total_credit)}
    async def dashboard(self, db, school_id, from_date=None, to_date=None):
        specs=[(FinanceInvoice,"total_amount","issue_date", "invoice_total", None),(FinanceInvoicePayment,"amount","payment_date","fees_collected",None),(Expense,"amount","expense_date","expenses",None),(PayrollRecord,"net_pay","payment_date","salaries_paid","PAID")]
        totals={}
        for model, amount_field, date_field, key, status in specs:
            stmt=select(func.coalesce(func.sum(getattr(model, amount_field)), 0)).where(model.school_id==school_id)
            if status: stmt=stmt.where(model.status==status)
            if from_date: stmt=stmt.where(getattr(model,date_field)>=from_date)
            if to_date: stmt=stmt.where(getattr(model,date_field)<=to_date)
            totals[key]=money((await db.execute(stmt)).scalar_one())
        outstanding_stmt=select(func.coalesce(func.sum(FinanceInvoice.total_amount - FinanceInvoice.amount_paid), 0)).where(FinanceInvoice.school_id==school_id,FinanceInvoice.status.in_(["ISSUED","PART_PAID","OVERDUE"]))
        totals["outstanding_fees"]=money((await db.execute(outstanding_stmt)).scalar_one())
        totals.update({"total_outflow":money(totals["expenses"]+totals["salaries_paid"]),"net_cash_movement":money(totals["fees_collected"]-totals["expenses"]-totals["salaries_paid"]),"from_date":from_date,"to_date":to_date})
        return totals


    async def reconciliation(self, db, school_id, from_date=None, to_date=None):
        stmt = select(FinanceInvoicePayment).where(FinanceInvoicePayment.school_id == school_id)
        if from_date: stmt = stmt.where(FinanceInvoicePayment.payment_date >= from_date)
        if to_date: stmt = stmt.where(FinanceInvoicePayment.payment_date <= to_date)
        payments = (await db.execute(stmt)).scalars().all()
        matched = [payment for payment in payments if payment.journal_entry_id]
        unmatched = [payment for payment in payments if not payment.journal_entry_id]
        return {"from_date": from_date, "to_date": to_date, "payment_count": len(payments), "reconciled_count": len(matched), "unreconciled_count": len(unmatched), "reconciled_amount": money(sum((p.amount for p in matched), Decimal("0.00"))), "unreconciled_amount": money(sum((p.amount for p in unmatched), Decimal("0.00"))), "unreconciled_payments": [{"id": p.id, "invoice_id": p.invoice_id, "reference": p.reference, "amount": p.amount, "payment_date": p.payment_date} for p in unmatched]}

accounting_service=AccountingService()
