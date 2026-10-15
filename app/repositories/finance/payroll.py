from app.models.finance.operations import FinanceSalaryProfile, PayrollRecord
from app.repositories.finance.base import FinanceRepository

salary_profile_repository = FinanceRepository(FinanceSalaryProfile)
payroll_repository = FinanceRepository(PayrollRecord)
