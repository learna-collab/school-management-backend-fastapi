from uuid import UUID, uuid4
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance.fee_category import FeeCategory
from app.models.finance.student_fee import StudentFee
from app.models.student import StudentProfile
from app.models.academic_session import AcademicSession
from app.models.terms import Term
from app.models.enrollment import StudentEnrollment
from app.models.classes import Class
from app.models.user import User
from app.models.finance.operations import FinanceAccount, FinanceInvoice, FinanceInvoiceLine, FinanceJournalEntry, FinanceJournalLine
from app.services.finance.common import ensure_default_accounts
from datetime import date
from app.repositories.finance.fees import fee_category_repository, student_fee_repository
from app.services.finance.common import get_school_row, money

class FeeService:
    async def list_categories(self, db: AsyncSession, school_id: UUID):
        return await fee_category_repository.list(db, school_id, limit=500)
    async def create_category(self, db: AsyncSession, school_id: UUID, name: str, description: str | None):
        name = name.strip()
        result = await db.execute(select(FeeCategory).where(FeeCategory.school_id == school_id, FeeCategory.name.ilike(name)))
        if result.scalar_one_or_none(): raise HTTPException(409, "Fee category already exists.")
        return await fee_category_repository.add(db, FeeCategory(school_id=school_id, name=name, description=description, is_active=True))
    async def assign_student_fee(self, db: AsyncSession, school_id: UUID, payload):
        await get_school_row(db, StudentProfile, school_id, payload.student_id, "Student")
        session = (await db.execute(select(AcademicSession).where(AcademicSession.id == payload.session_id))).scalar_one_or_none()
        term = (await db.execute(select(Term).where(Term.id == payload.term_id))).scalar_one_or_none()
        if not session or not term: raise HTTPException(404, "Academic session or term not found.")
        category = await get_school_row(db, FeeCategory, school_id, payload.fee_category_id, "Fee category")
        if not category.is_active: raise HTTPException(400, "Fee category is inactive.")
        duplicate = (await db.execute(select(StudentFee).where(StudentFee.school_id == school_id, StudentFee.student_id == payload.student_id, StudentFee.fee_category_id == payload.fee_category_id, StudentFee.session_id == payload.session_id, StudentFee.term_id == payload.term_id))).scalar_one_or_none()
        if duplicate: raise HTTPException(409, "This fee is already assigned for the selected student and academic period.")
        return await student_fee_repository.add(db, StudentFee(school_id=school_id, student_id=payload.student_id, fee_category_id=payload.fee_category_id, session_id=payload.session_id, term_id=payload.term_id, amount_due=money(payload.amount_due), note=payload.note))
    async def assign_fee_to_students(self, db: AsyncSession, school_id: UUID, user: User, payload):
        """Apply one term fee to all enrolled students or one selected class.

        Existing student/category/session/term assignments are preserved and counted
        as skipped, making repeat clicks safe rather than creating duplicate charges.
        """
        category = await get_school_row(db, FeeCategory, school_id, payload.fee_category_id, "Fee category")
        if not category.is_active:
            raise HTTPException(400, "This fee category is inactive.")
        session = (await db.execute(select(AcademicSession).where(AcademicSession.id == payload.session_id))).scalar_one_or_none()
        term = (await db.execute(select(Term).where(Term.id == payload.term_id))).scalar_one_or_none()
        if not session or not term:
            raise HTTPException(404, "Academic session or term not found.")
        if payload.scope == "CLASS":
            if not payload.class_id:
                raise HTTPException(422, "Choose a class for a class-specific fee.")
            await get_school_row(db, Class, school_id, payload.class_id, "Class")
        elif payload.class_id:
            raise HTTPException(422, "Do not provide a class when applying the fee to all students.")

        stmt = (
            select(StudentProfile.id)
            .join(StudentEnrollment, StudentEnrollment.student_id == StudentProfile.user_id)
            .where(
                StudentProfile.school_id == school_id,
                StudentEnrollment.school_id == school_id,
                StudentEnrollment.session_id == payload.session_id,
            )
        )
        if payload.scope == "CLASS":
            stmt = stmt.where(StudentEnrollment.class_id == payload.class_id)
        student_ids = list((await db.execute(stmt.distinct())).scalars().all())
        if not student_ids:
            raise HTTPException(404, "No enrolled students were found for the selected period and scope.")

        existing_rows = await db.execute(
            select(StudentFee.student_id).where(
                StudentFee.school_id == school_id,
                StudentFee.fee_category_id == payload.fee_category_id,
                StudentFee.session_id == payload.session_id,
                StudentFee.term_id == payload.term_id,
                StudentFee.student_id.in_(student_ids),
            )
        )
        existing = set(existing_rows.scalars().all())
        amount = money(payload.amount_due)
        new_student_ids = [student_id for student_id in student_ids if student_id not in existing]
        if not new_student_ids:
            return {
                "message": "This fee has already been applied to all students in the selected scope.",
                "category_name": category.name,
                "scope": payload.scope,
                "students_found": len(student_ids),
                "created_count": 0,
                "invoice_count": 0,
                "skipped_count": len(existing),
                "amount_per_student": str(amount),
                "session_id": str(payload.session_id),
                "term_id": str(payload.term_id),
            }

        # Fetch/create the standard accounts once, not once per student.
        await ensure_default_accounts(db, school_id)
        account_rows = await db.execute(
            select(FinanceAccount).where(
                FinanceAccount.school_id == school_id,
                FinanceAccount.code.in_(["1100", "4000"]),
            )
        )
        accounts_by_code = {account.code: account for account in account_rows.scalars().all()}
        receivable = accounts_by_code.get("1100")
        revenue = accounts_by_code.get("4000")
        if not receivable or not revenue:
            raise HTTPException(500, "School finance accounts could not be initialized. Please try again.")

        today = date.today()
        fee_rows = []
        invoice_rows = []
        line_rows = []
        journal_rows = []
        journal_line_rows = []
        for student_id in new_student_ids:
            fee_rows.append(StudentFee(
                id=uuid4(), school_id=school_id, student_id=student_id,
                fee_category_id=payload.fee_category_id, session_id=payload.session_id,
                term_id=payload.term_id, amount_due=amount, note=payload.note,
            ))
            invoice_id = uuid4()
            invoice_number = f"FEE-{payload.session_id.hex[:5].upper()}-{payload.term_id.hex[:4].upper()}-{payload.fee_category_id.hex[:4].upper()}-{student_id.hex[:8].upper()}"
            invoice_rows.append(FinanceInvoice(
                id=invoice_id, school_id=school_id, student_id=student_id,
                session_id=payload.session_id, term_id=payload.term_id,
                invoice_number=invoice_number, issue_date=today, total_amount=amount,
                amount_paid=money(0), status="ISSUED", note=payload.note, created_by=user.id,
            ))
            line_rows.append(FinanceInvoiceLine(
                id=uuid4(), school_id=school_id, invoice_id=invoice_id,
                fee_category_id=category.id, description=category.name,
                quantity=1, unit_amount=amount, line_total=amount,
            ))
            entry_id = uuid4()
            journal_rows.append(FinanceJournalEntry(
                id=entry_id, school_id=school_id,
                entry_number=f"INV-{invoice_id.hex[:12].upper()}", entry_date=today,
                source_type="INVOICE", source_id=invoice_id,
                description=f"Term fee invoice: {category.name} ({invoice_number})",
                status="POSTED", posted_by=user.id,
            ))
            journal_line_rows.extend([
                FinanceJournalLine(
                    id=uuid4(), school_id=school_id, entry_id=entry_id,
                    account_id=receivable.id, description="Student fee receivable",
                    debit=amount, credit=money(0),
                ),
                FinanceJournalLine(
                    id=uuid4(), school_id=school_id, entry_id=entry_id,
                    account_id=revenue.id, description="School fee revenue",
                    debit=money(0), credit=amount,
                ),
            ])

        # SQLAlchemy batches inserts per table during flush. Avoid per-student flushes
        # and the per-journal account lookups that made this endpoint slow at scale.
        db.add_all(fee_rows)
        db.add_all(invoice_rows)
        db.add_all(line_rows)
        db.add_all(journal_rows)
        db.add_all(journal_line_rows)
        await db.flush()
        return {
            "message": "Term fee applied successfully.",
            "category_name": category.name,
            "scope": payload.scope,
            "students_found": len(student_ids),
            "created_count": len(new_student_ids),
            "invoice_count": len(new_student_ids),
            "skipped_count": len(existing),
            "amount_per_student": str(amount),
            "session_id": str(payload.session_id),
            "term_id": str(payload.term_id),
        }

    async def list_student_fees(self, db: AsyncSession, school_id: UUID, student_id=None, session_id=None, term_id=None):
        stmt = select(StudentFee).where(StudentFee.school_id == school_id)
        for field, value in (("student_id", student_id), ("session_id", session_id), ("term_id", term_id)):
            if value: stmt = stmt.where(getattr(StudentFee, field) == value)
        return (await db.execute(stmt.order_by(StudentFee.created_at.desc()))).scalars().all()
fee_service = FeeService()
