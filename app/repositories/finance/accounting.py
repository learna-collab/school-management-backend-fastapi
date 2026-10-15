from app.models.finance.operations import FinanceAccount, FinanceJournalEntry, FinanceJournalLine
from app.repositories.finance.base import FinanceRepository

account_repository = FinanceRepository(FinanceAccount)
journal_entry_repository = FinanceRepository(FinanceJournalEntry)
journal_line_repository = FinanceRepository(FinanceJournalLine)
