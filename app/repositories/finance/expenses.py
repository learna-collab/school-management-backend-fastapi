from app.models.finance.expense import Expense
from app.models.finance.expense_category import ExpenseCategory
from app.repositories.finance.base import FinanceRepository

expense_repository = FinanceRepository(Expense)
expense_category_repository = FinanceRepository(ExpenseCategory)
