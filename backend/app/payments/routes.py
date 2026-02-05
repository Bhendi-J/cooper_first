"""Payment routes for Finternet integration."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.payments.services.finternet import FinternetService
from app.core import PaymentService, NotificationService
from app.extensions import db as mongo
from bson import ObjectId
import os
import logging

bp = Blueprint("payments", __name__)
logger = logging.getLogger(__name__)


@bp.route("/intent", methods=["POST"])
@jwt_required()
def create_intent():
    """
    Create a new payment intent via Finternet.
    
    Request body:
    {
        "amount": "100.00",
        "currency": "USDC",  // optional, defaults to USDC
        "description": "Payment for expense split"  // optional
    }
    
    Returns:
    {
        "id": "intent_xxx",
        "status": "INITIATED",
        "paymentUrl": "https://pay.fmm.finternetlab.io/?intent=intent_xxx",
        "amount": "100.00",
        "currency": "USDC"
    }
    """
    data = request.get_json() or {}
    
    amount = data.get("amount")
    if not amount:
        return jsonify({"error": "Amount is required"}), 400
    
    currency = data.get("currency", "USDC")
    description = data.get("description", "Cooper payment")
    
    try:
        finternet = FinternetService()
        result = finternet.create_payment_intent(
            amount=str(amount),
            currency=currency,
            description=description
        )
        
        logger.info(f"Finternet create_intent response: {result}")
        
        # Extract key info for frontend
        intent_data = result.get("data", result)
        intent_id = intent_data.get("id")
        
        # Look for payment URL in various possible locations
        payment_url = (
            intent_data.get("paymentUrl") or 
            intent_data.get("payment_url") or 
            intent_data.get("url") or
            result.get("paymentUrl") or
            result.get("payment_url") or
            result.get("url")
        )
        
        # If no payment URL from API, construct one for the Finternet payment page
        if not payment_url and intent_id:
            payment_url = f"https://pay.fmm.finternetlab.io/?intent={intent_id}"
        
        response = {
            "id": intent_id,
            "status": intent_data.get("status"),
            "paymentUrl": payment_url,
            "amount": intent_data.get("amount"),
            "currency": intent_data.get("currency", currency)
        }
        
        return jsonify(response), 201
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to create payment intent: {str(e)}"}), 500


@bp.route("/intent/<intent_id>", methods=["GET"])
@jwt_required()
def get_intent(intent_id):
    """
    Get the status of a payment intent.
    
    Returns:
    {
        "id": "intent_xxx",
        "status": "INITIATED|PROCESSING|SUCCEEDED|SETTLED|FINAL",
        "amount": "100.00",
        "currency": "USDC",
        "settlementStatus": "PENDING|IN_PROGRESS|COMPLETED"
    }
    """
    try:
        finternet = FinternetService()
        result = finternet.get_payment_intent(intent_id)
        
        intent_data = result.get("data", result)
        response = {
            "id": intent_data.get("id"),
            "status": intent_data.get("status"),
            "amount": intent_data.get("amount"),
            "currency": intent_data.get("currency"),
            "settlementStatus": intent_data.get("settlementStatus"),
            "transactionHash": intent_data.get("transactionHash"),
            "phases": intent_data.get("phases", [])
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get payment intent: {str(e)}"}), 500


@bp.route("/intent/<intent_id>/confirm", methods=["POST"])
@jwt_required()
def confirm_intent(intent_id):
    """
    Confirm a payment intent after user signs the transaction.
    
    Request body:
    {
        "signature": "0x...",
        "payerAddress": "0x..."
    }
    """
    data = request.get_json() or {}
    
    signature = data.get("signature")
    payer_address = data.get("payerAddress")
    
    if not signature or not payer_address:
        return jsonify({"error": "Signature and payerAddress are required"}), 400
    
    try:
        finternet = FinternetService()
        result = finternet.confirm_payment(intent_id, signature, payer_address)
        
        intent_data = result.get("data", result)
        response = {
            "id": intent_data.get("id"),
            "status": intent_data.get("status"),
            "transactionHash": intent_data.get("transactionHash"),
            "phases": intent_data.get("phases", [])
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Failed to confirm payment: {str(e)}"}), 500


@bp.route("/intent/<intent_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_intent(intent_id):
    """
    Cancel a pending payment intent.
    """
    try:
        finternet = FinternetService()
        result = finternet.cancel_payment(intent_id)
        
        intent_data = result.get("data", result)
        response = {
            "id": intent_data.get("id"),
            "status": intent_data.get("status")
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Failed to cancel payment: {str(e)}"}), 500


@bp.route("/split/calculate", methods=["POST"])
@jwt_required()
def calculate_split():
    """
    Calculate split amounts for participants.
    
    Request body:
    {
        "total": 100.00,
        "participants": 4,
        "weights": {"user1": 2, "user2": 1, "user3": 1}  // optional for unequal splits
    }
    
    Returns:
    {
        "total": 100.00,
        "num_participants": 4,
        "per_person": 25.00,
        "splits": {"participant_1": 25.00, ...},
        "currency": "USDC"
    }
    """
    from app.payments.services.finternet import calculate_split as calc_split
    
    data = request.get_json() or {}
    
    total = data.get("total")
    participants = data.get("participants")
    weights = data.get("weights")
    
    if not total or not participants:
        return jsonify({"error": "Total and participants are required"}), 400
    
    try:
        result = calc_split(float(total), int(participants), weights)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to calculate split: {str(e)}"}), 500


@bp.route("/mock/simulate-success/<intent_id>", methods=["POST"])
@jwt_required()
def simulate_success(intent_id):
    """
    [DEMO ONLY] Simulate a successful payment for hackathon demo.
    This endpoint instantly marks a payment as SUCCEEDED and triggers
    the deposit confirmation flow as if a webhook was received.
    """
    from app.core import PoolService, NotificationService
    
    try:
        # Find the payment record in various collections
        payment = mongo.payment_tracking.find_one({"intent_id": intent_id})
        if not payment:
            payment = mongo.payments.find_one({"finternet_id": intent_id})
        if not payment:
            # Also check payment_intents collection (used by deposit with Finternet)
            payment = mongo.payment_intents.find_one({"finternet_id": intent_id})
        if not payment:
            # Try by local ID or intent ID field
            payment = mongo.payment_intents.find_one({"intent_id": intent_id})
        
        if not payment:
            return jsonify({"error": "Payment not found"}), 404
        
        # Generate mock transaction hash
        import uuid
        tx_hash = "0x" + uuid.uuid4().hex + uuid.uuid4().hex[:24]
        
        # Update payment status to confirmed
        PaymentService.update_payment_status(
            intent_id,
            "confirmed",
            transaction_hash=tx_hash
        )
        
        # Get payment details - check both 'purpose' and 'intent_type' fields
        purpose = payment.get("purpose") or payment.get("intent_type")
        user_id = str(payment.get("user_id", ""))
        event_id = str(payment.get("event_id", "")) if payment.get("event_id") else None
        amount = float(payment.get("amount", 0))
        
        # Handle deposit purpose
        if purpose == "deposit" and event_id and user_id:
            success, message = PoolService.confirm_deposit(
                event_id=event_id,
                user_id=user_id,
                amount=amount,
                payment_id=intent_id
            )
            
            if success:
                NotificationService.notify_payment_confirmed(
                    user_id=user_id,
                    amount=amount,
                    purpose="Deposit"
                )
                logger.info(f"[MOCK] Deposit confirmed for user {user_id}, amount {amount}")
            else:
                logger.error(f"[MOCK] Failed to confirm deposit: {message}")
                return jsonify({"error": f"Failed to confirm deposit: {message}"}), 500
        
        # Handle wallet topup
        elif purpose == "wallet_topup" and user_id:
            from app.core import WalletFallbackService
            WalletFallbackService.credit_wallet(user_id, amount, intent_id)
            NotificationService.notify_payment_confirmed(
                user_id=user_id,
                amount=amount,
                purpose="Wallet Top-up"
            )
        
        response = {
            "id": intent_id,
            "status": "confirmed",
            "transactionHash": tx_hash,
            "amount": amount,
            "purpose": purpose,
            "message": "Payment simulated and deposit confirmed successfully"
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Failed to simulate payment: {str(e)}")
        return jsonify({"error": f"Failed to simulate payment: {str(e)}"}), 500


# ==================== WEBHOOK ENDPOINT ====================

@bp.route("/webhook", methods=["POST"])
def payment_webhook():
    """
    Webhook endpoint for Finternet payment gateway callbacks.
    
    This is the single source of truth for payment confirmations.
    No funds are credited until this webhook confirms the payment.
    
    Supports two payload formats:
    
    1. Finternet format:
    {
        "type": "payment_intent.succeeded",
        "data": {
            "id": "intent_xxx",
            "status": "SUCCEEDED",
            "transactionHash": "0x..."
        }
    }
    
    2. Simple format:
    {
        "intent_id": "intent_xxx",
        "status": "SUCCEEDED|FAILED|SETTLED",
        "transaction_hash": "0x...",
        "amount": "100.00"
    }
    
    Headers:
    - X-Finternet-Signature: HMAC signature for verification
    """
    from app.core import PoolService, NotificationService
    
    # Get raw body for signature verification
    raw_body = request.get_data(as_text=True)
    signature = request.headers.get("X-Finternet-Signature", "")
    
    # Verify webhook signature (skipped if no secret configured)
    webhook_secret = os.environ.get("FINTERNET_WEBHOOK_SECRET", "")
    if webhook_secret and not PaymentService.verify_webhook_signature(
        raw_body.encode(), signature, webhook_secret
    ):
        logger.warning("Invalid webhook signature received")
        return jsonify({"error": "Invalid signature"}), 401
    
    data = request.get_json() or {}
    
    # Normalize payload format
    # Handle Finternet's nested format: {"type": "...", "data": {...}}
    if "type" in data and "data" in data:
        event_type = data.get("type", "")
        intent_data = data.get("data", {})
        intent_id = intent_data.get("id")
        status = intent_data.get("status", "")
        tx_hash = intent_data.get("transactionHash")
    else:
        # Handle simple format: {"intent_id": "...", "status": "..."}
        intent_id = data.get("intent_id")
        status = data.get("status", "")
        tx_hash = data.get("transaction_hash")
        # Convert to event_type format
        if status in ["SUCCEEDED", "SETTLED", "FINAL"]:
            event_type = "payment_intent.succeeded"
        elif status == "FAILED":
            event_type = "payment_intent.failed"
        elif status == "CANCELLED":
            event_type = "payment_intent.cancelled"
        else:
            event_type = "payment_intent.processing"
    
    if not intent_id:
        return jsonify({"error": "Missing intent_id"}), 400
    
    # Check for duplicate/replay
    if PaymentService.is_duplicate_callback(intent_id, event_type):
        logger.info(f"Duplicate webhook ignored for intent: {intent_id}")
        return jsonify({"message": "Already processed"}), 200
    
    try:
        # Find the payment record in our tracking
        payment = mongo.payment_tracking.find_one({"intent_id": intent_id})
        if not payment:
            payment = mongo.payments.find_one({"finternet_id": intent_id})
        
        if not payment:
            logger.warning(f"Payment record not found for intent: {intent_id}")
            return jsonify({"error": "Payment record not found"}), 404
        
        # Record callback for idempotency
        callback_id = PaymentService.record_callback(intent_id, event_type, data)
        
        # Process based on event type
        if event_type == "payment_intent.succeeded":
            # Update payment status
            PaymentService.update_payment_status(
                intent_id,
                "confirmed",
                transaction_hash=tx_hash
            )
            
            # Get payment details
            purpose = payment.get("purpose")
            user_id = str(payment.get("user_id", ""))
            event_id = str(payment.get("event_id", "")) if payment.get("event_id") else None
            amount = float(payment.get("amount", 0))
            
            # Handle deposit purpose
            if purpose == "deposit" and event_id and user_id:
                success, message = PoolService.confirm_deposit(
                    event_id=event_id,
                    user_id=user_id,
                    amount=amount,
                    payment_id=intent_id
                )
                
                if success:
                    NotificationService.notify_payment_confirmed(
                        user_id=user_id,
                        amount=amount,
                        purpose="Deposit"
                    )
                    logger.info(f"Deposit confirmed for user {user_id}, amount {amount}")
                else:
                    logger.error(f"Failed to confirm deposit: {message}")
            
            # Handle wallet topup
            elif purpose == "wallet_topup" and user_id:
                from app.core import WalletFallbackService
                WalletFallbackService.credit_wallet(user_id, amount, intent_id)
                NotificationService.notify_payment_confirmed(
                    user_id=user_id,
                    amount=amount,
                    purpose="Wallet Top-up"
                )
            
            PaymentService.mark_callback_processed(callback_id)
            return jsonify({
                "message": "Payment confirmed",
                "status": "success"
            }), 200
            
        elif event_type == "payment_intent.failed":
            PaymentService.update_payment_status(
                intent_id,
                "failed",
                error_message=data.get("error", "Payment failed")
            )
            PaymentService.mark_callback_processed(callback_id)
            return jsonify({
                "message": "Payment failure recorded",
                "status": "failed"
            }), 200
            
        elif event_type == "payment_intent.cancelled":
            PaymentService.update_payment_status(intent_id, "cancelled")
            PaymentService.mark_callback_processed(callback_id)
            return jsonify({
                "message": "Payment cancellation recorded",
                "status": "cancelled"
            }), 200
        
        else:
            PaymentService.update_payment_status(intent_id, "processing")
            PaymentService.mark_callback_processed(callback_id)
            return jsonify({
                "message": "Payment processing",
                "status": "processing"
            }), 200
            
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({"error": "Internal error"}), 500


@bp.route("/status/<intent_id>", methods=["GET"])
@jwt_required()
def get_payment_tracking_status(intent_id):
    """
    Get the status of a payment from our tracking records.
    
    This is used by the frontend to poll for payment completion
    after the user is redirected back from the payment gateway.
    
    Also checks Finternet API and auto-confirms deposit if payment succeeded.
    """
    from app.core import PoolService, NotificationService
    
    user_id = get_jwt_identity()
    
    # Check payment_tracking collection first
    payment = mongo.payment_tracking.find_one({"intent_id": intent_id})
    if not payment:
        payment = mongo.payments.find_one({"finternet_id": intent_id})
    if not payment:
        # Also check payment_intents collection (used by Finternet deposits)
        payment = mongo.payment_intents.find_one({"finternet_id": intent_id})
    if not payment:
        payment = mongo.payment_intents.find_one({"intent_id": intent_id})
    
    if not payment:
        return jsonify({"error": "Payment not found"}), 404
    
    # Verify user owns this payment
    payment_user_id = str(payment.get("user_id", ""))
    if payment_user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    
    current_status = payment.get("status", "initiated")
    
    # Get purpose - check both fields
    purpose = payment.get("purpose") or payment.get("intent_type")
    
    # If not yet confirmed, check Finternet API for status
    if current_status not in ["confirmed", "failed", "cancelled"]:
        try:
            finternet = FinternetService()
            finternet_data = finternet.get_payment_intent(intent_id)
            finternet_status = finternet_data.get("status") or finternet_data.get("data", {}).get("status")
            
            logger.info(f"Finternet status for {intent_id}: {finternet_status}")
            
            # If Finternet says succeeded, confirm the deposit
            if finternet_status in ["SUCCEEDED", "SETTLED", "FINAL"]:
                tx_hash = finternet_data.get("transactionHash") or finternet_data.get("data", {}).get("transactionHash")
                
                # Update our tracking status
                PaymentService.update_payment_status(
                    intent_id,
                    "confirmed",
                    transaction_hash=tx_hash
                )
                
                # Confirm the deposit
                event_id = str(payment.get("event_id", "")) if payment.get("event_id") else None
                amount = float(payment.get("amount", 0))
                
                if purpose == "deposit" and event_id:
                    success, message = PoolService.confirm_deposit(
                        event_id=event_id,
                        user_id=user_id,
                        amount=amount,
                        payment_id=intent_id
                    )
                    
                    if success:
                        NotificationService.notify_payment_confirmed(
                            user_id=user_id,
                            amount=amount,
                            purpose="Deposit"
                        )
                        logger.info(f"Auto-confirmed deposit for user {user_id}, amount {amount}")
                    else:
                        logger.error(f"Failed to auto-confirm deposit: {message}")
                
                elif purpose == "wallet_topup":
                    from app.core import WalletFallbackService
                    WalletFallbackService.credit_wallet(user_id, amount, intent_id)
                    NotificationService.notify_payment_confirmed(
                        user_id=user_id,
                        amount=amount,
                        purpose="Wallet Top-up"
                    )
                
                current_status = "confirmed"
                payment["transaction_hash"] = tx_hash
                
            elif finternet_status == "CANCELLED":
                PaymentService.update_payment_status(intent_id, "cancelled")
                current_status = "cancelled"
                
            elif finternet_status == "PROCESSING":
                current_status = "processing"
                
        except Exception as e:
            logger.warning(f"Could not check Finternet status: {str(e)}")
            # Continue with our local status
    
    response = {
        "intent_id": intent_id,
        "status": current_status,
        "amount": payment.get("amount"),
        "purpose": purpose,
        "event_id": str(payment.get("event_id", "")) if payment.get("event_id") else None,
        "transaction_hash": payment.get("transaction_hash"),
        "created_at": payment.get("created_at").isoformat() if payment.get("created_at") else None,
        "confirmed_at": payment.get("confirmed_at").isoformat() if payment.get("confirmed_at") else None
    }
    
    return jsonify(response), 200


@bp.route("/deposit", methods=["POST"])
@jwt_required()
def create_deposit_intent():
    """
    Create a payment intent for an event deposit.
    
    Request body:
    {
        "event_id": "...",
        "amount": 100.00
    }
    
    Returns payment intent with URL for user to complete payment.
    """
    from app.core import RuleEnforcementService, ReliabilityService, PoolService
    
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    event_id = data.get("event_id")
    amount = data.get("amount")
    
    if not event_id or not amount:
        return jsonify({"error": "event_id and amount are required"}), 400
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400
    
    # Get event
    event = mongo.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Check reliability-based adjustments
    rules = event.get("rules", {})
    adjusted_rules = ReliabilityService.apply_reliability_adjustments(
        user_id, event_id, rules
    )
    
    # Check if user is restricted from making deposits
    tier = adjusted_rules.get("reliability_tier", "good")
    if tier == "restricted":
        return jsonify({
            "error": "Your account is restricted. Please settle outstanding debts.",
            "tier": tier
        }), 403
    
    # Apply any deposit multiplier from reliability tier
    deposit_multiplier = ReliabilityService.get_tier_restrictions(tier).get("join_deposit_multiplier", 1.0)
    if deposit_multiplier > 1.0:
        # This is for informational purposes - actual enforcement is on minimum deposits
        pass
    
    # Validate against rules
    # Returns: (is_valid, error_message, violation_type)
    is_valid, error_message, violation_type = RuleEnforcementService.validate_deposit(event_id, user_id, amount)
    if not is_valid:
        return jsonify({
            "error": "Deposit violates event rules",
            "violations": [{"type": violation_type, "message": error_message}]
        }), 400
    
    # Create payment intent with metadata
    try:
        finternet = FinternetService()
        result = finternet.create_payment_intent(
            amount=str(amount),
            currency="USDC",
            description=f"Deposit for {event.get('name', 'event')}"
        )
        
        logger.info(f"Finternet response: {result}")
        
        intent_data = result.get("data", result)
        intent_id = intent_data.get("id")
        
        # Look for payment URL in various possible locations
        payment_url = (
            intent_data.get("paymentUrl") or 
            intent_data.get("payment_url") or 
            intent_data.get("url") or
            result.get("paymentUrl") or
            result.get("payment_url") or
            result.get("url")
        )
        
        # If no payment URL from API, construct one for the Finternet payment page
        if not payment_url and intent_id:
            # Finternet payment page URL pattern
            payment_url = f"https://pay.fmm.finternetlab.io/?intent={intent_id}"
        
        # Store payment tracking record
        mongo.payment_tracking.insert_one({
            "intent_id": intent_id,
            "user_id": ObjectId(user_id),
            "event_id": ObjectId(event_id),
            "purpose": "deposit",
            "amount": amount,
            "status": "initiated",
            "created_at": __import__('datetime').datetime.utcnow()
        })
        
        return jsonify({
            "id": intent_id,
            "status": intent_data.get("status"),
            "paymentUrl": payment_url,
            "amount": amount,
            "currency": "USDC"
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to create deposit intent: {str(e)}"}), 500


@bp.route("/topup", methods=["POST"])
@jwt_required()
def create_topup_intent():
    """
    Create a payment intent for personal wallet top-up.
    
    Request body:
    {
        "amount": 50.00
    }
    """
    from app.core import WalletFallbackService
    
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    amount = data.get("amount")
    
    if not amount:
        return jsonify({"error": "amount is required"}), 400
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400
    
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400
    
    try:
        finternet = FinternetService()
        result = finternet.create_payment_intent(
            amount=str(amount),
            currency="USDC",
            description="Wallet top-up"
        )
        
        intent_data = result.get("data", result)
        intent_id = intent_data.get("id")
        
        # Store payment tracking record
        mongo.payment_tracking.insert_one({
            "intent_id": intent_id,
            "user_id": ObjectId(user_id),
            "purpose": "wallet_topup",
            "amount": amount,
            "status": "initiated",
            "created_at": __import__('datetime').datetime.utcnow()
        })
        
        return jsonify({
            "id": intent_id,
            "status": intent_data.get("status"),
            "paymentUrl": intent_data.get("paymentUrl"),
            "amount": amount,
            "currency": "USDC"
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to create top-up intent: {str(e)}"}), 500


@bp.route("/debts/settle", methods=["POST"])
@jwt_required()
def create_debt_settlement_intent():
    """
    Create a payment intent to settle outstanding debts.
    
    Request body:
    {
        "debt_id": "...",  // optional - specific debt
        "amount": 50.00   // optional - partial settlement
    }
    """
    from app.core import DebtService
    
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    debt_id = data.get("debt_id")
    amount = data.get("amount")
    
    # Get outstanding debts
    if debt_id:
        debt = mongo.debts.find_one({
            "_id": ObjectId(debt_id),
            "user_id": ObjectId(user_id),
            "status": {"$in": ["outstanding", "partially_paid"]}
        })
        if not debt:
            return jsonify({"error": "Debt not found"}), 404
        
        if not amount:
            amount = debt.get("remaining_amount", debt.get("amount", 0))
    else:
        # Get total outstanding
        outstanding = DebtService.get_user_debts(user_id)
        if not outstanding:
            return jsonify({"error": "No outstanding debts"}), 400
        
        total_outstanding = sum(d.get("remaining_amount", d.get("amount", 0)) for d in outstanding)
        amount = amount or total_outstanding
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400
    
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400
    
    try:
        finternet = FinternetService()
        result = finternet.create_payment_intent(
            amount=str(amount),
            currency="USDC",
            description="Debt settlement"
        )
        
        intent_data = result.get("data", result)
        intent_id = intent_data.get("id")
        
        # Store payment tracking record
        mongo.payment_tracking.insert_one({
            "intent_id": intent_id,
            "user_id": ObjectId(user_id),
            "debt_id": ObjectId(debt_id) if debt_id else None,
            "purpose": "debt_settlement",
            "amount": amount,
            "status": "initiated",
            "created_at": __import__('datetime').datetime.utcnow()
        })
        
        return jsonify({
            "id": intent_id,
            "status": intent_data.get("status"),
            "paymentUrl": intent_data.get("paymentUrl"),
            "amount": amount,
            "currency": "USDC"
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to create settlement intent: {str(e)}"}), 500