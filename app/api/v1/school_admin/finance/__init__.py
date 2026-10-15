from fastapi import APIRouter
from .fees import router as fees_router
from .invoices import router as invoices_router
from .expenses import router as expenses_router
from .payroll import router as payroll_router
from .accounting import router as accounting_router

router = APIRouter(prefix="/school-admin/finance", tags=["School Finance"])
router.include_router(fees_router)
router.include_router(invoices_router)
router.include_router(expenses_router)
router.include_router(payroll_router)
router.include_router(accounting_router)
