from datetime import date
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.student import StudentProfile
from app.models.academic_session import AcademicSession
from app.models.terms import Term
from app.models.finance.fee_category import FeeCategory
from app.models.finance.operations import FinanceAccount, FinanceInvoice, FinanceInvoiceLine, FinanceInvoicePayment
from app.repositories.finance.invoices import invoice_repository, invoice_payment_repository
from app.services.finance.common import money, get_school_row, ensure_default_accounts, require_account, post_journal

class InvoiceService:
    async def create(self, db: AsyncSession, school_id: UUID, user: User, payload):
        await get_school_row(db, StudentProfile, school_id, payload.student_id, "Student")
        if not (await db.execute(select(AcademicSession).where(AcademicSession.id == payload.session_id))).scalar_one_or_none() or not (await db.execute(select(Term).where(Term.id == payload.term_id))).scalar_one_or_none():
            raise HTTPException(404, "Academic session or term not found.")
        if payload.due_date and payload.due_date < payload.issue_date: raise HTTPException(400, "Due date cannot be before issue date.")
        duplicate = (await db.execute(select(FinanceInvoice).where(FinanceInvoice.school_id == school_id, FinanceInvoice.invoice_number == payload.invoice_number.strip()))).scalar_one_or_none()
        if duplicate: raise HTTPException(409, "Invoice number already exists.")
        total = Decimal("0.00")
        for line in payload.lines:
            if line.fee_category_id:
                cat = await get_school_row(db, FeeCategory, school_id, line.fee_category_id, "Fee category")
                if not cat.is_active: raise HTTPException(400, "Cannot invoice an inactive fee category.")
            total += money(line.unit_amount * line.quantity)
        invoice = FinanceInvoice(school_id=school_id, student_id=payload.student_id, session_id=payload.session_id, term_id=payload.term_id, invoice_number=payload.invoice_number.strip(), issue_date=payload.issue_date, due_date=payload.due_date, total_amount=money(total), amount_paid=Decimal("0.00"), status="ISSUED", note=payload.note, created_by=user.id)
        await invoice_repository.add(db, invoice)
        for line in payload.lines:
            db.add(FinanceInvoiceLine(school_id=school_id, invoice_id=invoice.id, fee_category_id=line.fee_category_id, description=line.description, quantity=line.quantity, unit_amount=money(line.unit_amount), line_total=money(line.unit_amount * line.quantity)))
        await ensure_default_accounts(db, school_id)
        receivable = (await db.execute(select(FinanceAccount).where(FinanceAccount.school_id == school_id, FinanceAccount.code == "1100"))).scalar_one()
        revenue = (await db.execute(select(FinanceAccount).where(FinanceAccount.school_id == school_id, FinanceAccount.code == "4000"))).scalar_one()
        await post_journal(db, school_id, user.id, f"INV-{invoice.id.hex[:12].upper()}", payload.issue_date, "INVOICE", invoice.id, f"Invoice issued: {invoice.invoice_number}", [(receivable.id, "Student fees receivable", invoice.total_amount, 0), (revenue.id, "School fees revenue", 0, invoice.total_amount)])
        await db.flush(); return invoice
    async def list(self, db: AsyncSession, school_id: UUID, student_id=None, status=None, limit=100, offset=0):
        stmt = (
            select(FinanceInvoice, StudentProfile, User)
            .join(StudentProfile, StudentProfile.id == FinanceInvoice.student_id)
            .join(User, User.id == StudentProfile.user_id)
            .where(FinanceInvoice.school_id == school_id)
        )
        if student_id: stmt = stmt.where(FinanceInvoice.student_id == student_id)
        if status: stmt = stmt.where(FinanceInvoice.status == status.upper())
        rows = (await db.execute(stmt.order_by(FinanceInvoice.created_at.desc()).limit(limit).offset(offset))).all()
        return [
            {
                **{column.key: getattr(invoice, column.key) for column in FinanceInvoice.__table__.columns},
                "student_name": " ".join(part for part in [user.first_name, user.last_name] if part).strip() or user.email,
                "admission_number": student.admission_number,
            }
            for invoice, student, user in rows
        ]
    async def get(self, db: AsyncSession, school_id: UUID, invoice_id: UUID):
        invoice = await get_school_row(db, FinanceInvoice, school_id, invoice_id, "Invoice")
        lines = (await db.execute(select(FinanceInvoiceLine).where(FinanceInvoiceLine.invoice_id == invoice.id, FinanceInvoiceLine.school_id == school_id))).scalars().all()
        payments = (await db.execute(select(FinanceInvoicePayment).where(FinanceInvoicePayment.invoice_id == invoice.id, FinanceInvoicePayment.school_id == school_id).order_by(FinanceInvoicePayment.payment_date.desc()))).scalars().all()
        return {"invoice": invoice, "lines": lines, "payments": payments, "balance_due": money(invoice.total_amount - invoice.amount_paid)}
    async def record_payment(self, db: AsyncSession, school_id: UUID, user: User, invoice_id: UUID, payload):
        await ensure_default_accounts(db, school_id)
        invoice = await get_school_row(db, FinanceInvoice, school_id, invoice_id, "Invoice")
        if invoice.status in {"VOID", "CANCELLED"}: raise HTTPException(400, "Cannot collect payment against a void or cancelled invoice.")
        if money(invoice.amount_paid + payload.amount) > money(invoice.total_amount): raise HTTPException(400, "Payment exceeds the invoice balance.")
        account = await require_account(db, school_id, payload.receiving_account_id, {"ASSET"})
        payment = FinanceInvoicePayment(school_id=school_id, invoice_id=invoice.id, amount=money(payload.amount), payment_method=payload.payment_method, payment_date=payload.payment_date, reference=payload.reference.strip(), receiving_account_id=account.id, note=payload.note, received_by=user.id)
        await invoice_payment_repository.add(db, payment)
        invoice.amount_paid = money(invoice.amount_paid + payload.amount)
        invoice.status = "PAID" if invoice.amount_paid == invoice.total_amount else "PART_PAID"
        receivable = (await db.execute(select(FinanceAccount).where(FinanceAccount.school_id == school_id, FinanceAccount.code == "1100"))).scalar_one()
        entry = await post_journal(db, school_id, user.id, f"RCPT-{payment.id.hex[:12].upper()}", payload.payment_date, "INVOICE_PAYMENT", payment.id, f"Invoice {invoice.invoice_number} payment", [(account.id, "Cash/bank received", payload.amount, 0), (receivable.id, "Reduce student fees receivable", 0, payload.amount)])
        payment.journal_entry_id = entry.id; await db.flush()
        return {"payment": payment, "invoice": invoice, "journal_entry_id": entry.id}

invoice_service = InvoiceService()
