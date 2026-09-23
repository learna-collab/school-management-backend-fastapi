import hashlib
import hmac
import secrets

import httpx

from app.core.config import settings


class PaystackService:
    BASE_URL = "https://api.paystack.co"

    # ============================================================
    # HEADERS
    # ============================================================

    def headers(self):
        return {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    # ============================================================
    # INITIALIZE TRANSACTION
    # ============================================================

    async def initialize_transaction(
        self,
        email: str,
        amount_kobo: int,
        callback_url: str,
        checkout_id: str | None = None,
    ):
        reference = secrets.token_hex(12)

        payload = {
            "email": email,
            "amount": amount_kobo,
            "callback_url": callback_url,
            "reference": reference,
        }

        # --------------------------------------------------------
        # STORE CHECKOUT ID IN PAYSTACK METADATA
        # --------------------------------------------------------

        if checkout_id:
            payload["metadata"] = {
                "checkout_id": checkout_id,
            }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/transaction/initialize",
                headers=self.headers(),
                json=payload,
            )

        response.raise_for_status()

        data = response.json()

        if not data.get("status"):
            raise Exception(
                data.get(
                    "message",
                    "Unable to initialize Paystack transaction.",
                )
            )

        transaction = data.get("data") or {}

        return {
            "reference": transaction["reference"],
            "authorization_url": transaction["authorization_url"],
            "access_code": transaction["access_code"],
        }

    # ============================================================
    # VERIFY TRANSACTION
    # ============================================================

    async def verify_transaction(
        self,
        reference: str,
    ):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=self.headers(),
            )

        response.raise_for_status()

        data = response.json()

        if not data.get("status"):
            raise Exception(
                data.get(
                    "message",
                    "Unable to verify Paystack transaction.",
                )
            )

        transaction = data.get("data") or {}

        customer = transaction.get("customer") or {}
        authorization = transaction.get("authorization") or {}

        return {
            "paid": transaction.get("status") == "success",
            "reference": transaction.get("reference"),
            "amount": transaction.get("amount", 0),
            "transaction_id": str(transaction.get("id")),
            "authorization_code": authorization.get("authorization_code"),
            "email": customer.get("email"),
            "status": transaction.get("status"),
        }

    # ============================================================
    # CREATE TRANSFER RECIPIENT
    # ============================================================

    async def create_transfer_recipient(
        self,
        name: str,
        account_number: str,
        bank_code: str,
    ):
        payload = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/transferrecipient",
                headers=self.headers(),
                json=payload,
            )

        response.raise_for_status()

        data = response.json()

        if not data.get("status"):
            raise Exception(
                data.get(
                    "message",
                    "Unable to create transfer recipient.",
                )
            )

        return data["data"]["recipient_code"]

    # ============================================================
    # INITIATE TRANSFER
    # ============================================================

    async def transfer(
        self,
        recipient_code: str,
        amount_kobo: int,
        reference: str | None = None,
    ):
        # --------------------------------------------------------
        # PAYSTACK TRANSFER REFERENCE
        #
        # A unique reference makes the transfer request
        # identifiable and helps protect against accidental
        # duplicate payout requests.
        # --------------------------------------------------------

        transfer_reference = (
            reference if reference else f"MKT-{secrets.token_hex(12).upper()}"
        )

        payload = {
            "source": "balance",
            "reason": "Marketplace payout",
            "amount": amount_kobo,
            "recipient": recipient_code,
            "reference": transfer_reference,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/transfer",
                headers=self.headers(),
                json=payload,
            )

        response.raise_for_status()

        data = response.json()

        if not data.get("status"):
            raise Exception(
                data.get(
                    "message",
                    "Unable to create transfer.",
                )
            )

        transfer_data = data.get("data") or {}

        return {
            "transfer_code": transfer_data["transfer_code"],
            "status": transfer_data["status"],
            "reference": transfer_data.get(
                "reference",
                transfer_reference,
            ),
        }

    # ============================================================
    # VERIFY TRANSFER
    # ============================================================

    async def verify_transfer(
        self,
        transfer_code: str,
    ):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.BASE_URL}/transfer/{transfer_code}",
                headers=self.headers(),
            )

        response.raise_for_status()

        data = response.json()

        if not data.get("status"):
            raise Exception(
                data.get(
                    "message",
                    "Unable to verify Paystack transfer.",
                )
            )

        transfer = data.get("data") or {}

        return {
            "transfer_code": transfer.get("transfer_code"),
            "reference": transfer.get("reference"),
            "status": transfer.get("status"),
            "amount": transfer.get("amount", 0),
            "recipient": transfer.get("recipient"),
        }

    # ============================================================
    # WEBHOOK SIGNATURE
    # ============================================================

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        computed = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode(),
            payload,
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(
            computed,
            signature,
        )
