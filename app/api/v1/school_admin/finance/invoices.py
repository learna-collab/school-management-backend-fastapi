from datetime import date
from uuid import UUID
from fastapi import APIRouter, Query
from sqlalchemy import select
from app.core.deps import DBSession, RequireSchoolAdmin
from app.models.finance.operations import FinanceInvoicePayment
from app.schemas.finance.invoices import InvoiceCreate, InvoicePaymentCreate
from app.services.finance.common import require_school, money
from app.services.finance.invoices import invoice_service

router = APIRouter()
def invoice_out(row):
    if isinstance(row, dict):
        result = dict(row)
        result["balance_due"] = money(result["total_amount"] - result["amount_paid"])
        return result
    return {"id":row.id,"school_id":row.school_id,"student_id":row.student_id,"session_id":row.session_id,"term_id":row.term_id,"invoice_number":row.invoice_number,"issue_date":row.issue_date,"due_date":row.due_date,"total_amount":row.total_amount,"amount_paid":row.amount_paid,"balance_due":money(row.total_amount-row.amount_paid),"status":row.status,"note":row.note,"created_at":row.created_at}
@router.post("/invoices", status_code=201)
async def create_invoice(payload: InvoiceCreate, db: DBSession, user: RequireSchoolAdmin):
    return invoice_out(await invoice_service.create(db, require_school(user), user, payload))
@router.get("/invoices")
async def list_invoices(db: DBSession, user: RequireSchoolAdmin, student_id: UUID | None = None, invoice_status: str | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    rows=await invoice_service.list(db, require_school(user), student_id, invoice_status, limit, offset)
    return [invoice_out(row) for row in rows]
@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: UUID, db: DBSession, user: RequireSchoolAdmin):
    data=await invoice_service.get(db, require_school(user), invoice_id)
    return {**invoice_out(data["invoice"]),"lines":data["lines"],"payments":data["payments"]}
@router.post("/invoices/{invoice_id}/payments", status_code=201)
async def record_payment(invoice_id: UUID, payload: InvoicePaymentCreate, db: DBSession, user: RequireSchoolAdmin):
    data=await invoice_service.record_payment(db, require_school(user), user, invoice_id, payload)
    return {"payment":data["payment"],"invoice":invoice_out(data["invoice"]),"journal_entry_id":data["journal_entry_id"]}
@router.get("/payments")
async def list_payments(db: DBSession, user: RequireSchoolAdmin, invoice_id: UUID | None = None, from_date: date | None = None, to_date: date | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    school_id=require_school(user)
    stmt=select(FinanceInvoicePayment).where(FinanceInvoicePayment.school_id==school_id)
    if invoice_id: stmt=stmt.where(FinanceInvoicePayment.invoice_id==invoice_id)
    if from_date: stmt=stmt.where(FinanceInvoicePayment.payment_date>=from_date)
    if to_date: stmt=stmt.where(FinanceInvoicePayment.payment_date<=to_date)
    return (await db.execute(stmt.order_by(FinanceInvoicePayment.payment_date.desc()).limit(limit).offset(offset))).scalars().all()
