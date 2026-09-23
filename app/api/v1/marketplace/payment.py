from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Header,
    HTTPException,
    Request,
    status,
)

from app.core.deps import (
    CurrentUser,
    DBSession,
    RequireSuperAdmin,
)
from app.services.payment_service import (
    MarketplacePaymentService,
)

router = APIRouter(
    prefix="/marketplace/payments",
    tags=["Marketplace Payments"],
)

service = MarketplacePaymentService()


# ============================================================
# INITIALIZE CHECKOUT PAYMENT
# ============================================================


@router.post(
    "/checkouts/{checkout_id}/initialize",
    status_code=status.HTTP_200_OK,
)
async def initialize_checkout_payment(
    checkout_id: UUID,
    user: CurrentUser,
    callback_url: str = Body(...),
    db: DBSession = None,
):
    """
    Initialize one Paystack transaction for the entire checkout.

    A checkout may contain multiple vendor orders, but the customer
    pays once for the complete checkout amount.
    """
    payment = await service.initialize_checkout(
        db=db,
        checkout_id=checkout_id,
        customer_id=user.id,
        customer_email=user.email,
        callback_url=callback_url,
    )

    return {
        "checkout_id": str(checkout_id),
        "reference": payment.reference,
        "checkout_url": payment.authorization_url,
        "access_code": payment.access_code,
        "amount": payment.amount,
        "status": (
            payment.status.value if hasattr(payment.status, "value") else payment.status
        ),
    }


# ============================================================
# VERIFY PAYMENT
# ============================================================


@router.get(
    "/verify",
    status_code=status.HTTP_200_OK,
)
async def verify_payment(
    reference: str,
    db: DBSession,
):
    """
    Verify a Paystack payment by reference.

    Verification is idempotent. If the payment has already been
    processed, the existing successful payment state is returned.
    """
    checkout = await service.verify_payment(
        db=db,
        reference=reference,
    )

    return {
        "message": "Payment verified.",
        "checkout_id": str(checkout.id),
        "checkout_number": checkout.checkout_number,
        "status": (
            checkout.status.value
            if hasattr(checkout.status, "value")
            else checkout.status
        ),
        "total_amount": checkout.total_amount,
        "currency": checkout.currency,
    }


# ============================================================
# PAYSTACK WEBHOOK
# ============================================================


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
)
async def paystack_webhook(
    request: Request,
    db: DBSession,
    x_paystack_signature: str = Header(...),
):
    payload = await request.body()

    if not service.paystack.verify_webhook_signature(
        payload,
        x_paystack_signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Paystack signature.",
        )

    event = await request.json()

    event_type = event.get("event")

    data = event.get("data") or {}

    # --------------------------------------------------
    # CUSTOMER PAYMENT SUCCESS
    # --------------------------------------------------
    if event_type == "charge.success":
        reference = data.get("reference")

        if reference:
            await service.verify_payment(
                db=db,
                reference=reference,
            )

    # --------------------------------------------------
    # CUSTOMER PAYMENT FAILED
    # --------------------------------------------------
    elif event_type == "charge.failed":
        reference = data.get("reference")

        if reference:
            await service.fail_payment(
                db=db,
                reference=reference,
            )

    # --------------------------------------------------
    # VENDOR PAYOUT SUCCESS / FAILURE
    # --------------------------------------------------
    elif event_type in {
        "transfer.success",
        "transfer.failed",
        "transfer.reversed",
    }:
        await service.handle_transfer_webhook(
            db=db,
            event=event,
        )

    return {
        "message": "Webhook processed.",
    }


# ============================================================
# RELEASE VENDOR PAYMENT
# ============================================================


@router.post(
    "/orders/{order_id}/release",
    status_code=status.HTTP_200_OK,
)
async def release_payment(
    order_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    """
    Release a vendor's held payment after delivery confirmation.

    Only Super Admin can release vendor payment.
    """
    return await service.release_vendor_payment(
        db=db,
        order_id=order_id,
    )
