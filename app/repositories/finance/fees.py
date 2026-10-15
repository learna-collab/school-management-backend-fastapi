from app.models.finance.fee_category import FeeCategory
from app.models.finance.student_fee import StudentFee
from app.repositories.finance.base import FinanceRepository

fee_category_repository = FinanceRepository(FeeCategory)
student_fee_repository = FinanceRepository(StudentFee)
