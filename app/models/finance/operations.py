from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class FinanceInvoice(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "finance_invoices"
    __table_args__ = (
        UniqueConstraint(
            "school_id", "invoice_number", name="uq_finance_invoice_school_number"
        ),
        CheckConstraint("total_amount >= 0", name="invoice_total_nonnegative"),
        CheckConstraint("amount_paid >= 0", name="invoice_paid_nonnegative"),
        Index("ix_finance_invoice_school_student", "school_id", "student_id"),
    )
    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    term_id: Mapped[UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="RESTRICT"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(60), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ISSUED", index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class FinanceInvoiceLine(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "finance_invoice_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="invoice_line_quantity_positive"),
        CheckConstraint("unit_amount >= 0", name="invoice_line_amount_nonnegative"),
    )
    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fee_category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("fee_categories.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    unit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class FinanceInvoicePayment(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "finance_invoice_payments"
    __table_args__ = (
        UniqueConstraint(
            "school_id", "reference", name="uq_finance_invoice_payment_reference"
        ),
        CheckConstraint("amount > 0", name="invoice_payment_amount_positive"),
    )
    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance_invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    reference: Mapped[str] = mapped_column(String(100), nullable=False)
    receiving_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("finance_accounts.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    journal_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("finance_journal_entries.id", ondelete="SET NULL"), nullable=True
    )


class FinanceAccount(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "finance_accounts"
    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_finance_account_school_code"),
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class FinanceJournalEntry(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "finance_journal_entries"
    __table_args__ = (
        UniqueConstraint(
            "school_id", "entry_number", name="uq_finance_journal_school_number"
        ),
    )
    entry_number: Mapped[str] = mapped_column(String(60), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="POSTED")
    posted_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class FinanceJournalLine(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "finance_journal_lines"
    __table_args__ = (
        CheckConstraint("debit >= 0", name="journal_debit_nonnegative"),
        CheckConstraint("credit >= 0", name="journal_credit_nonnegative"),
        CheckConstraint("NOT (debit > 0 AND credit > 0)", name="journal_line_one_side"),
    )
    entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance_journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    debit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )


class PayrollRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "finance_payroll_records"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "employee_user_id",
            "pay_year",
            "pay_month",
            name="uq_finance_payroll_employee_period",
        ),
        CheckConstraint(
            "basic_salary >= 0 AND allowances >= 0 AND deductions >= 0",
            name="payroll_amounts_nonnegative",
        ),
    )
    employee_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    pay_year: Mapped[int] = mapped_column(nullable=False)
    pay_month: Mapped[int] = mapped_column(nullable=False)
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    allowances: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT", index=True
    )
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("finance_accounts.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    journal_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("finance_journal_entries.id", ondelete="SET NULL"), nullable=True
    )


class FinanceSalaryProfile(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "finance_salary_profiles"
    __table_args__ = (
        UniqueConstraint(
            "school_id", "employee_user_id", name="uq_finance_salary_profile_employee"
        ),
        CheckConstraint(
            "basic_salary >= 0 AND default_allowances >= 0 AND default_deductions >= 0",
            name="salary_profile_amounts_nonnegative",
        ),
    )
    employee_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    default_allowances: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    default_deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
