"""
Payment Service - Secure payment handling with webhook-based confirmation.

Responsibilities:
- Handle Finternet payment gateway callbacks
- Prevent duplicate confirmations and replay attacks
- Track payment status (pending, confirmed, failed)
- Link payments to purpose (deposit, expense, debt repayment, etc.)
"""
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from bson import ObjectId
import hashlib
import hmac
import os

from app.extensions import db as mongo


class PaymentPurpose:
    """Payment purpose constants."""
    DEPOSIT = "deposit"
    JOIN_PAYMENT = "join_payment"
    WALLET_TOPUP = "wallet_topup"
    EXPENSE_SETTLEMENT = "expense_settlement"
    DEBT_REPAYMENT = "debt_repayment"
    REFUND = "refund"


class PaymentStatus:
    """Payment status constants."""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentService:
    """Service for secure payment handling."""
    
    WEBHOOK_SECRET = os.environ.get("FINTERNET_WEBHOOK_SECRET", "")
    
    @classmethod
    def verify_webhook_signature(cls, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature to prevent forgery.
        
        Args:
            payload: Raw request body bytes
            signature: Signature from webhook header
            
        Returns:
            True if signature is valid
        """
        if not cls.WEBHOOK_SECRET:
            # For development, skip verification if no secret configured
            return True
        
        expected = hmac.new(
            cls.WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    @classmethod
    def is_duplicate_callback(cls, finternet_id: str, event_type: str) -> bool:
        """
        Check if we've already processed this callback (prevent duplicates).
        
        Args:
            finternet_id: Finternet payment intent ID
            event_type: Type of callback event
            
        Returns:
            True if this callback was already processed
        """
        existing = mongo.payment_callbacks.find_one({
            "finternet_id": finternet_id,
            "event_type": event_type,
            "processed": True
        })
        return existing is not None
    
    @classmethod
    def record_callback(cls, finternet_id: str, event_type: str, data: Dict) -> str:
        """
        Record a webhook callback for idempotency.
        
        Args:
            finternet_id: Finternet payment intent ID
            event_type: Type of callback event
            data: Callback payload data
            
        Returns:
            Callback record ID
        """
        record = {
            "finternet_id": finternet_id,
            "event_type": event_type,
            "data": data,
            "processed": False,
            "created_at": datetime.utcnow()
        }
        result = mongo.payment_callbacks.insert_one(record)
        return str(result.inserted_id)
    
    @classmethod
    def mark_callback_processed(cls, callback_id: str) -> None:
        """Mark a callback as successfully processed."""
        mongo.payment_callbacks.update_one(
            {"_id": ObjectId(callback_id)},
            {
                "$set": {
                    "processed": True,
                    "processed_at": datetime.utcnow()
                }
            }
        )
    
    @classmethod
    def create_payment_record(
        cls,
        finternet_id: str,
        user_id: str,
        amount: float,
        currency: str,
        purpose: str,
        event_id: Optional[str] = None,
        expense_id: Optional[str] = None,
        debt_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create a local payment record linked to its purpose.
        
        Args:
            finternet_id: Finternet payment intent ID
            user_id: User making the payment
            amount: Payment amount
            currency: Currency code
            purpose: Payment purpose (deposit, expense, etc.)
            event_id: Related event ID (optional)
            expense_id: Related expense ID (optional)
            debt_id: Related debt ID (optional)
            metadata: Additional metadata
            
        Returns:
            Payment record ID
        """
        record = {
            "finternet_id": finternet_id,
            "user_id": user_id,
            "amount": float(amount),
            "currency": currency,
            "purpose": purpose,
            "status": PaymentStatus.PENDING,
            "event_id": event_id,
            "expense_id": expense_id,
            "debt_id": debt_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = mongo.payments.insert_one(record)
        return str(result.inserted_id)
    
    @classmethod
    def get_payment_by_finternet_id(cls, finternet_id: str) -> Optional[Dict]:
        """Get payment record by Finternet ID."""
        payment = mongo.payments.find_one({"finternet_id": finternet_id})
        if payment:
            payment["_id"] = str(payment["_id"])
        return payment
    
    @classmethod
    def update_payment_status(
        cls,
        finternet_id: str,
        status: str,
        transaction_hash: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update payment status.
        
        Args:
            finternet_id: Finternet payment intent ID
            status: New status
            transaction_hash: Blockchain transaction hash (if confirmed)
            error_message: Error message (if failed)
            
        Returns:
            True if updated, False if not found
        """
        update = {
            "$set": {
                "status": status,
                "updated_at": datetime.utcnow()
            }
        }
        
        if transaction_hash:
            update["$set"]["transaction_hash"] = transaction_hash
        
        if error_message:
            update["$set"]["error_message"] = error_message
        
        if status == PaymentStatus.CONFIRMED:
            update["$set"]["confirmed_at"] = datetime.utcnow()
            update["$set"]["status"] = "confirmed"  # Normalize status
        elif status == PaymentStatus.FAILED:
            update["$set"]["failed_at"] = datetime.utcnow()
        
        # Try updating in payments collection
        result = mongo.payments.update_one(
            {"finternet_id": finternet_id},
            update
        )
        
        # Also update in payment_tracking collection (used by deposit/topup routes)
        result2 = mongo.payment_tracking.update_one(
            {"intent_id": finternet_id},
            update
        )
        
        # Also update in payment_intents collection (used by Finternet deposits)
        result3 = mongo.payment_intents.update_one(
            {"finternet_id": finternet_id},
            update
        )
        
        # Also try by intent_id field
        result4 = mongo.payment_intents.update_one(
            {"intent_id": finternet_id},
            update
        )
        
        return result.modified_count > 0 or result2.modified_count > 0 or result3.modified_count > 0 or result4.modified_count > 0
    
    @classmethod
    def process_webhook(
        cls,
        payload: bytes,
        signature: str
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Process a payment webhook from Finternet.
        
        This is the source of truth for payment confirmation.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature
            
        Returns:
            Tuple of (success, message, payment_data)
        """
        import json
        
        # Verify signature
        if not cls.verify_webhook_signature(payload, signature):
            return False, "Invalid webhook signature", None
        
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return False, "Invalid JSON payload", None
        
        event_type = data.get("type", "")
        intent_data = data.get("data", {})
        finternet_id = intent_data.get("id")
        
        if not finternet_id:
            return False, "Missing payment intent ID", None
        
        # Check for duplicate
        if cls.is_duplicate_callback(finternet_id, event_type):
            return True, "Callback already processed", None
        
        # Record callback for idempotency
        callback_id = cls.record_callback(finternet_id, event_type, data)
        
        try:
            # Get local payment record - check multiple collections
            payment = cls.get_payment_by_finternet_id(finternet_id)
            if not payment:
                # Check payment_tracking collection (used by deposit/topup routes)
                payment = mongo.payment_tracking.find_one({"intent_id": finternet_id})
                if payment:
                    payment["_id"] = str(payment["_id"])
                    # Normalize fields for consistent handling
                    payment["finternet_id"] = payment.get("intent_id")
                    payment["user_id"] = str(payment.get("user_id", ""))
                    payment["event_id"] = str(payment.get("event_id", "")) if payment.get("event_id") else None
            if not payment:
                # Check payment_intents collection (legacy)
                payment = mongo.payment_intents.find_one({"finternet_id": finternet_id})
                if payment:
                    payment["_id"] = str(payment["_id"])
            
            # Process based on event type
            if event_type == "payment_intent.succeeded":
                tx_hash = intent_data.get("transactionHash")
                
                # Update payment status
                cls.update_payment_status(
                    finternet_id,
                    PaymentStatus.CONFIRMED,
                    transaction_hash=tx_hash
                )
                
                # Trigger purpose-specific handlers
                if payment:
                    cls._handle_confirmed_payment(payment, intent_data)
                
                cls.mark_callback_processed(callback_id)
                return True, "Payment confirmed", payment
                
            elif event_type == "payment_intent.failed":
                error = intent_data.get("error", {})
                cls.update_payment_status(
                    finternet_id,
                    PaymentStatus.FAILED,
                    error_message=error.get("message", "Payment failed")
                )
                
                cls.mark_callback_processed(callback_id)
                return True, "Payment failed", payment
                
            elif event_type == "payment_intent.cancelled":
                cls.update_payment_status(
                    finternet_id,
                    PaymentStatus.CANCELLED
                )
                
                cls.mark_callback_processed(callback_id)
                return True, "Payment cancelled", payment
            
            elif event_type == "payment_intent.processing":
                cls.update_payment_status(
                    finternet_id,
                    PaymentStatus.PROCESSING
                )
                
                cls.mark_callback_processed(callback_id)
                return True, "Payment processing", payment
            
            else:
                # Unknown event type - log but don't fail
                cls.mark_callback_processed(callback_id)
                return True, f"Unknown event type: {event_type}", None
                
        except Exception as e:
            # Don't mark as processed on error so it can be retried
            return False, f"Processing error: {str(e)}", None
    
    @classmethod
    def _handle_confirmed_payment(cls, payment: Dict, intent_data: Dict) -> None:
        """
        Handle confirmed payment based on purpose.
        
        This triggers the appropriate business logic updates.
        """
        from .pool_service import PoolService
        from .debt_service import DebtService
        from .notification_service import NotificationService
        
        purpose = payment.get("purpose") or payment.get("intent_type")
        user_id = payment.get("user_id")
        event_id = payment.get("event_id")
        amount = float(payment.get("amount", 0))
        
        if purpose == PaymentPurpose.DEPOSIT or purpose == "deposit":
            # Update user's contribution and pool
            if event_id and user_id:
                PoolService.confirm_deposit(
                    event_id=event_id,
                    user_id=user_id,
                    amount=amount,
                    payment_id=payment.get("finternet_id") or payment.get("_id")
                )
                
                # Notify user
                NotificationService.notify_payment_confirmed(
                    user_id=user_id,
                    amount=amount,
                    purpose="Deposit"
                )
        
        elif purpose == PaymentPurpose.EXPENSE_SETTLEMENT:
            expense_id = payment.get("expense_id")
            if expense_id:
                # Mark split as paid
                mongo.split_payments.update_one(
                    {"expense_id": ObjectId(expense_id), "user_id": user_id},
                    {
                        "$set": {
                            "status": "paid",
                            "paid_at": datetime.utcnow()
                        }
                    }
                )
                
                NotificationService.notify_payment_confirmed(
                    user_id=user_id,
                    amount=amount,
                    purpose="Expense Settlement"
                )
        
        elif purpose == PaymentPurpose.DEBT_REPAYMENT:
            debt_id = payment.get("debt_id")
            if debt_id:
                DebtService.settle_debt(
                    debt_id=debt_id,
                    payment_id=payment.get("finternet_id") or payment.get("_id"),
                    amount=amount
                )
                
                NotificationService.notify_payment_confirmed(
                    user_id=user_id,
                    amount=amount,
                    purpose="Debt Repayment"
                )
        
        elif purpose == PaymentPurpose.WALLET_TOPUP:
            if user_id:
                from .wallet_service import WalletFallbackService
                WalletFallbackService.credit_wallet(
                    user_id=user_id,
                    amount=amount,
                    source="topup",
                    reference_id=payment.get("finternet_id") or payment.get("_id")
                )
                
                NotificationService.notify_payment_confirmed(
                    user_id=user_id,
                    amount=amount,
                    purpose="Wallet Top-up"
                )
        
        elif purpose == PaymentPurpose.JOIN_PAYMENT:
            if event_id and user_id:
                from .join_service import JoinRequestService
                JoinRequestService.confirm_join_payment(
                    event_id=event_id,
                    user_id=user_id,
                    amount=amount,
                    payment_id=payment.get("finternet_id") or payment.get("_id")
                )
    
    @classmethod
    def get_user_payments(
        cls,
        user_id: str,
        status: Optional[str] = None,
        purpose: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """Get payments for a user with optional filters."""
        query = {"user_id": user_id}
        
        if status:
            query["status"] = status
        
        if purpose:
            query["purpose"] = purpose
        
        payments = list(
            mongo.payments.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        
        for p in payments:
            p["_id"] = str(p["_id"])
        
        return payments
    
    @classmethod
    def validate_client_confirmation(
        cls,
        finternet_id: str,
        user_id: str
    ) -> Tuple[bool, str]:
        """
        Validate a client-side payment confirmation.
        
        Client confirmations are for UX only - actual confirmation
        must come from webhook. This checks if webhook already confirmed.
        
        Args:
            finternet_id: Finternet payment intent ID
            user_id: User claiming the payment
            
        Returns:
            Tuple of (is_valid, message)
        """
        payment = cls.get_payment_by_finternet_id(finternet_id)
        
        if not payment:
            # Check legacy collection
            payment = mongo.payment_intents.find_one({"finternet_id": finternet_id})
        
        if not payment:
            return False, "Payment not found"
        
        # Verify user owns this payment
        if payment.get("user_id") != user_id:
            return False, "Payment does not belong to user"
        
        # Check if already confirmed via webhook
        if payment.get("status") == PaymentStatus.CONFIRMED:
            return True, "Payment already confirmed"
        
        if payment.get("status") == PaymentStatus.FAILED:
            return False, "Payment failed"
        
        if payment.get("status") == PaymentStatus.CANCELLED:
            return False, "Payment was cancelled"
        
        # Still pending - webhook hasn't arrived yet
        return False, "Payment pending confirmation from gateway"
