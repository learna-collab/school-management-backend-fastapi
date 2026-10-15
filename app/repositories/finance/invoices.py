from app.models.finance.operations import FinanceInvoice, FinanceInvoiceLine, FinanceInvoicePayment
from app.repositories.finance.base import FinanceRepository

invoice_repository = FinanceRepository(FinanceInvoice)
invoice_line_repository = FinanceRepository(FinanceInvoiceLine)
invoice_payment_repository = FinanceRepository(FinanceInvoicePayment)
