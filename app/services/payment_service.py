import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.marketplace.marketplace_checkout import (
    CheckoutStatus,
    MarketplaceCheckout,
)
from app.models.marketplace.marketplace_order import (
    MarketplaceOrder,
    OrderStatus,
)
from app.models.marketplace.marketplace_payment import (
    MarketplacePayment,
    MarketplaceWallet,
    PaymentStatus,
)
from app.models.marketplace.marketplace_payout import (
    MarketplacePayout,
    PayoutStatus,
)
from app.models.marketplace.marketplace_vendor_bank import (
    VendorBankAccount,
)
from app.services.marketplace.checkout_service import CheckoutService
from app.services.paystack_service import PaystackService

CENT = Decimal("0.01")


class MarketplacePaymentService:
    def __init__(self):
        self.paystack = PaystackService()

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    # ============================================================
    # INITIALIZE CHECKOUT PAYMENT
    # ============================================================

    async def initialize_checkout(
        self,
        db: AsyncSession,
        checkout_id: uuid.UUID,
        customer_id: uuid.UUID,
        customer_email: str,
        callback_url: str,
    ):
        result = await db.execute(
            select(MarketplaceCheckout)
            .where(
                MarketplaceCheckout.id == checkout_id,
                MarketplaceCheckout.customer_id == customer_id,
            )
            .options(
                selectinload(MarketplaceCheckout.orders),
                selectinload(MarketplaceCheckout.payment),
            )
        )

        checkout = result.scalar_one_or_none()

        if not checkout:
            raise HTTPException(
                status_code=404,
                detail="Checkout not found.",
            )

        # --------------------------------------------------------
        # CHECKOUT STATUS
        # --------------------------------------------------------

        if checkout.status == CheckoutStatus.PAID:
            raise HTTPException(
                status_code=400,
                detail="This checkout has already been paid.",
            )

        if checkout.status != CheckoutStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Checkout cannot be paid because its status is "
                    f"{checkout.status.value}."
                ),
            )

        # --------------------------------------------------------
        # AMOUNT
        # --------------------------------------------------------

        checkout_amount = self._money(Decimal(checkout.total_amount))

        if checkout_amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Checkout amount must be greater than zero.",
            )

        # --------------------------------------------------------
        # REUSE EXISTING PENDING PAYMENT
        #
        # This prevents multiple Paystack transactions from being
        # created if the customer clicks Pay more than once.
        # --------------------------------------------------------

        existing_payment = checkout.payment

        if existing_payment:
            if existing_payment.status == PaymentStatus.SUCCESS:
                raise HTTPException(
                    status_code=400,
                    detail="This checkout has already been paid.",
                )

            if (
                existing_payment.status == PaymentStatus.PENDING
                and existing_payment.authorization_url
            ):
                return existing_payment

        # --------------------------------------------------------
        # PAYSTACK AMOUNT
        # --------------------------------------------------------

        amount_kobo = int(checkout_amount * Decimal("100"))

        # --------------------------------------------------------
        # INITIALIZE PAYSTACK
        # --------------------------------------------------------

        paystack_response = await self.paystack.initialize_transaction(
            email=customer_email,
            amount_kobo=amount_kobo,
            callback_url=callback_url,
            checkout_id=str(checkout.id),
        )

        # --------------------------------------------------------
        # UPDATE EXISTING PAYMENT
        # --------------------------------------------------------

        if existing_payment:
            existing_payment.amount = checkout_amount
            existing_payment.reference = paystack_response["reference"]
            existing_payment.access_code = paystack_response["access_code"]
            existing_payment.authorization_url = paystack_response["authorization_url"]
            existing_payment.status = PaymentStatus.PENDING

            await db.commit()
            await db.refresh(existing_payment)

            return existing_payment

        # --------------------------------------------------------
        # CREATE PAYMENT
        # --------------------------------------------------------

        payment = MarketplacePayment(
            checkout_id=checkout.id,
            amount=checkout_amount,
            reference=paystack_response["reference"],
            access_code=paystack_response["access_code"],
            authorization_url=paystack_response["authorization_url"],
            status=PaymentStatus.PENDING,
        )

        db.add(payment)

        await db.commit()
        await db.refresh(payment)

        return payment

    # ============================================================
    # VERIFY PAYMENT
    # ============================================================

    async def verify_payment(
        self,
        db: AsyncSession,
        reference: str,
    ):
        # --------------------------------------------------------
        # LOAD PAYMENT + CHECKOUT
        # --------------------------------------------------------

        result = await db.execute(
            select(MarketplacePayment)
            .where(
                MarketplacePayment.reference == reference,
            )
            .options(
                selectinload(MarketplacePayment.checkout).selectinload(
                    MarketplaceCheckout.orders
                )
            )
        )

        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="Payment not found.",
            )

        checkout = payment.checkout

        if not checkout:
            raise HTTPException(
                status_code=400,
                detail="Payment checkout not found.",
            )

        # --------------------------------------------------------
        # IDEMPOTENCY
        #
        # If the webhook already processed this payment, simply
        # return the checkout.
        #
        # This prevents:
        #
        # webhook -> wallet credit
        # browser -> wallet credit again
        # --------------------------------------------------------

        if payment.status == PaymentStatus.SUCCESS:
            return checkout

        # --------------------------------------------------------
        # VERIFY DIRECTLY WITH PAYSTACK
        # --------------------------------------------------------

        verification = await self.paystack.verify_transaction(reference)

        if not verification["paid"]:
            payment.status = PaymentStatus.FAILED

            await db.commit()

            raise HTTPException(
                status_code=400,
                detail="Payment was not successful.",
            )

        # --------------------------------------------------------
        # VERIFY AMOUNT
        #
        # Never trust only the Paystack "paid" status.
        # The amount paid must equal our checkout amount.
        # --------------------------------------------------------

        expected_amount_kobo = int(
            self._money(Decimal(payment.amount)) * Decimal("100")
        )

        actual_amount_kobo = int(verification["amount"])

        if actual_amount_kobo != expected_amount_kobo:
            payment.status = PaymentStatus.FAILED

            await db.commit()

            raise HTTPException(
                status_code=400,
                detail="Payment amount does not match checkout amount.",
            )

        # --------------------------------------------------------
        # LOCK PAYMENT
        #
        # Re-read the payment with a row lock so concurrent
        # webhook/browser verification cannot both credit wallets.
        # --------------------------------------------------------

        locked_payment_result = await db.execute(
            select(MarketplacePayment)
            .where(
                MarketplacePayment.id == payment.id,
            )
            .with_for_update()
        )

        locked_payment = locked_payment_result.scalar_one()

        if locked_payment.status == PaymentStatus.SUCCESS:
            await db.rollback()

            return checkout

        # --------------------------------------------------------
        # MARK PAYMENT SUCCESS
        # --------------------------------------------------------

        locked_payment.status = PaymentStatus.SUCCESS

        locked_payment.paystack_transaction_id = verification.get("transaction_id")

        locked_payment.authorization_code = verification.get("authorization_code")

        locked_payment.paid_at = datetime.now(UTC)

        # --------------------------------------------------------
        # MARK CHECKOUT PAID
        # --------------------------------------------------------

        checkout.status = CheckoutStatus.PAID

        # --------------------------------------------------------
        # PROCESS EACH VENDOR ORDER
        #
        # One checkout may contain:
        #
        # Vendor A -> Order A
        # Vendor B -> Order B
        # Vendor C -> Order C
        #
        # Each vendor gets only its own vendor_amount credited
        # to pending_balance.
        # --------------------------------------------------------

        for order in checkout.orders:
            # ----------------------------------------------------
            # IDEMPOTENCY AT ORDER LEVEL
            # ----------------------------------------------------

            if order.status == OrderStatus.PAID_HELD:
                continue

            if order.status != OrderStatus.PENDING:
                continue

            order.status = OrderStatus.PAID_HELD

            # ----------------------------------------------------
            # LOCK VENDOR WALLET
            # ----------------------------------------------------

            wallet_result = await db.execute(
                select(MarketplaceWallet)
                .where(MarketplaceWallet.vendor_id == order.vendor_id)
                .with_for_update()
            )

            wallet = wallet_result.scalar_one_or_none()

            # ----------------------------------------------------
            # CREATE WALLET IF IT DOES NOT EXIST
            # ----------------------------------------------------

            if not wallet:
                wallet = MarketplaceWallet(
                    vendor_id=order.vendor_id,
                    available_balance=Decimal("0.00"),
                    pending_balance=Decimal("0.00"),
                )

                db.add(wallet)

                await db.flush()

            # ----------------------------------------------------
            # CREDIT PENDING BALANCE
            # ----------------------------------------------------

            wallet.pending_balance = self._money(
                Decimal(wallet.pending_balance) + Decimal(order.vendor_amount)
            )

        # --------------------------------------------------------
        # COMMIT EVERYTHING TOGETHER
        # --------------------------------------------------------

        await db.commit()

        # --------------------------------------------------------
        # RETURN FRESH CHECKOUT
        # --------------------------------------------------------

        result = await db.execute(
            select(MarketplaceCheckout)
            .where(MarketplaceCheckout.id == checkout.id)
            .options(selectinload(MarketplaceCheckout.orders))
        )

        return result.scalar_one()

    # ============================================================
    # RELEASE VENDOR PAYMENT
    # ============================================================

    async def release_vendor_payment(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
    ):
        # ============================================================
        # LOAD + LOCK ORDER
        # ============================================================

        result = await db.execute(
            select(MarketplaceOrder)
            .where(
                MarketplaceOrder.id == order_id,
            )
            .with_for_update()
        )

        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        # ============================================================
        # DELIVERY
        # ============================================================

        if not order.delivery_confirmed:
            raise HTTPException(
                status_code=400,
                detail="Delivery has not been confirmed.",
            )

        # ============================================================
        # ALREADY RELEASED
        # ============================================================

        if order.released:
            raise HTTPException(
                status_code=400,
                detail="Payment already released.",
            )

        # ============================================================
        # CHECK EXISTING PAYOUT
        # ============================================================

        payout_result = await db.execute(
            select(MarketplacePayout)
            .where(
                MarketplacePayout.order_id == order.id,
            )
            .with_for_update()
        )

        existing_payout = payout_result.scalar_one_or_none()

        if existing_payout:
            if existing_payout.status == PayoutStatus.SUCCESS:
                raise HTTPException(
                    status_code=400,
                    detail="Payment has already been released.",
                )

            if existing_payout.status == PayoutStatus.PROCESSING:
                return {
                    "message": "Vendor payment is already being processed.",
                    "reference": existing_payout.reference,
                    "transfer_code": existing_payout.transfer_code,
                    "status": existing_payout.status.value,
                }

        # ============================================================
        # BANK ACCOUNT
        # ============================================================

        bank_result = await db.execute(
            select(VendorBankAccount)
            .where(VendorBankAccount.vendor_id == order.vendor_id)
            .with_for_update()
        )

        bank = bank_result.scalar_one_or_none()

        if not bank:
            raise HTTPException(
                status_code=400,
                detail="Vendor bank account missing.",
            )

        # ============================================================
        # WALLET
        # ============================================================

        wallet_result = await db.execute(
            select(MarketplaceWallet)
            .where(MarketplaceWallet.vendor_id == order.vendor_id)
            .with_for_update()
        )

        wallet = wallet_result.scalar_one_or_none()

        if not wallet:
            raise HTTPException(
                status_code=400,
                detail="Vendor wallet not found.",
            )

        vendor_amount = self._money(Decimal(order.vendor_amount))

        pending_balance = self._money(Decimal(wallet.pending_balance))

        if pending_balance < vendor_amount:
            raise HTTPException(
                status_code=400,
                detail="Insufficient pending vendor balance.",
            )

        # ============================================================
        # CREATE PAYSTACK RECIPIENT
        # ============================================================

        if not bank.recipient_code:
            bank.recipient_code = await self.paystack.create_transfer_recipient(
                name=bank.account_name,
                account_number=bank.account_number,
                bank_code=bank.bank_code,
            )

            await db.flush()

        # ============================================================
        # CREATE UNIQUE PAYOUT REFERENCE
        # ============================================================

        payout_reference = f"PAYOUT-{uuid.uuid4().hex[:20].upper()}"

        # ============================================================
        # INITIATE PAYSTACK TRANSFER
        # ============================================================

        transfer = await self.paystack.transfer(
            recipient_code=bank.recipient_code,
            amount_kobo=int(vendor_amount * Decimal("100")),
            reference=payout_reference,
        )

        transfer_code = transfer.get("transfer_code")

        if not transfer_code:
            raise HTTPException(
                status_code=400,
                detail="Paystack did not return a transfer code.",
            )

        # ============================================================
        # CREATE PAYOUT
        # ============================================================

        payout = MarketplacePayout(
            vendor_id=order.vendor_id,
            order_id=order.id,
            amount=vendor_amount,
            bank_code=bank.bank_code,
            account_number=bank.account_number,
            recipient_code=bank.recipient_code,
            reference=payout_reference,
            transfer_code=transfer_code,
            status=PayoutStatus.PROCESSING,
        )

        db.add(payout)

        # ============================================================
        # IMPORTANT
        #
        # DO NOT:
        #
        # wallet.pending_balance -= vendor_amount
        # wallet.available_balance += vendor_amount
        #
        # AND DO NOT:
        #
        # order.released = True
        # order.status = COMPLETED
        #
        # yet.
        #
        # Paystack has only accepted the transfer request.
        # We wait for transfer.success.
        # ============================================================

        await db.commit()

        return {
            "message": "Vendor payment transfer initiated.",
            "reference": payout_reference,
            "transfer_code": transfer_code,
            "status": PayoutStatus.PROCESSING.value,
        }

    async def handle_transfer_webhook(
        self,
        db: AsyncSession,
        event: dict,
    ):
        event_type = event.get("event")
        data = event.get("data") or {}

        # ============================================================
        # WE ONLY PROCESS TRANSFER EVENTS HERE
        # ============================================================

        if event_type not in {
            "transfer.success",
            "transfer.failed",
            "transfer.reversed",
        }:
            return {
                "message": "Event ignored.",
                "event": event_type,
            }

        transfer_code = data.get("transfer_code")
        reference = data.get("reference")

        if not transfer_code and not reference:
            raise HTTPException(
                status_code=400,
                detail="Transfer reference not provided.",
            )

        # ============================================================
        # FIND PAYOUT
        # ============================================================

        if transfer_code:
            result = await db.execute(
                select(MarketplacePayout)
                .where(MarketplacePayout.transfer_code == transfer_code)
                .with_for_update()
            )

            payout = result.scalar_one_or_none()
        else:
            result = await db.execute(
                select(MarketplacePayout)
                .where(MarketplacePayout.reference == reference)
                .with_for_update()
            )

            payout = result.scalar_one_or_none()

        if not payout:
            raise HTTPException(
                status_code=404,
                detail="Marketplace payout not found.",
            )

        # ============================================================
        # SUCCESS
        # ============================================================

        if event_type == "transfer.success":
            # --------------------------------------------------------
            # IDEMPOTENCY
            # --------------------------------------------------------

            if payout.status == PayoutStatus.SUCCESS:
                return {
                    "message": "Payout already processed.",
                    "reference": payout.reference,
                    "status": payout.status.value,
                }

            # --------------------------------------------------------
            # LOCK WALLET
            # --------------------------------------------------------

            wallet_result = await db.execute(
                select(MarketplaceWallet)
                .where(MarketplaceWallet.vendor_id == payout.vendor_id)
                .with_for_update()
            )

            wallet = wallet_result.scalar_one_or_none()

            if not wallet:
                raise HTTPException(
                    status_code=400,
                    detail="Vendor wallet not found.",
                )

            payout_amount = self._money(Decimal(payout.amount))

            pending_balance = self._money(Decimal(wallet.pending_balance))

            if pending_balance < payout_amount:
                raise HTTPException(
                    status_code=400,
                    detail="Vendor pending balance is insufficient.",
                )

            # --------------------------------------------------------
            # MOVE FUNDS
            #
            # NOW it is safe because Paystack confirmed success.
            # --------------------------------------------------------

            wallet.pending_balance = self._money(pending_balance - payout_amount)

            wallet.available_balance = self._money(
                Decimal(wallet.available_balance) + payout_amount
            )

            # --------------------------------------------------------
            # MARK PAYOUT SUCCESS
            # --------------------------------------------------------

            payout.status = PayoutStatus.SUCCESS

            # --------------------------------------------------------
            # COMPLETE ORDER
            # --------------------------------------------------------

            order_result = await db.execute(
                select(MarketplaceOrder)
                .where(MarketplaceOrder.id == payout.order_id)
                .with_for_update()
            )

            order = order_result.scalar_one_or_none()

            if order:
                order.released = True
                order.status = OrderStatus.COMPLETED

            await db.commit()

            return {
                "message": "Vendor payout completed successfully.",
                "reference": payout.reference,
                "transfer_code": payout.transfer_code,
                "status": payout.status.value,
            }

        # ============================================================
        # FAILED / REVERSED
        # ============================================================

        if event_type in {
            "transfer.failed",
            "transfer.reversed",
        }:
            # --------------------------------------------------------
            # ALREADY FAILED
            # --------------------------------------------------------

            if payout.status == PayoutStatus.FAILED:
                return {
                    "message": "Payout already marked as failed.",
                    "reference": payout.reference,
                    "status": payout.status.value,
                }

            payout.status = PayoutStatus.FAILED

            await db.commit()

            return {
                "message": "Vendor payout marked as failed.",
                "reference": payout.reference,
                "transfer_code": payout.transfer_code,
                "status": payout.status.value,
            }

        return {
            "message": "Transfer event processed.",
        }

    async def fail_payment(
        self,
        db: AsyncSession,
        reference: str,
    ):
        result = await db.execute(
            select(MarketplacePayment)
            .where(
                MarketplacePayment.reference == reference,
            )
            .options(selectinload(MarketplacePayment.checkout))
            .with_for_update()
        )

        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found.",
            )

        checkout = payment.checkout

        # Payment has already succeeded.
        # Never restore stock in this situation.
        if payment.status == PaymentStatus.SUCCESS:
            return checkout

        # If checkout is already paid, do nothing.
        if checkout.status == CheckoutStatus.PAID:
            return checkout

        payment.status = PaymentStatus.FAILED

        checkout.status = CheckoutStatus.FAILED

        await CheckoutService.restore_checkout_stock(
            db=db,
            checkout_id=checkout.id,
        )

        await db.commit()

        return checkout
