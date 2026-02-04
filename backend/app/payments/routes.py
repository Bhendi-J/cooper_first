"""
Payment routes for Finternet integration.

Endpoints:
- POST /payments/intent - Create a payment intent
- GET /payments/intent/<id> - Get payment intent details
- POST /payments/intent/<id>/confirm - Confirm payment with signature
- POST /payments/intent/<id>/cancel - Cancel payment intent
- GET /payments/pending - Get user's pending payments
- GET /payments/intent/<id>/escrow - Get conditional payment details
- POST /payments/intent/<id>/escrow/delivery-proof - Submit delivery proof
- POST /payments/intent/<id>/escrow/dispute - Raise a dispute
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime

from app.extensions import db as mongo
from app.payments.services.finternet import FinternetService
from app.payments.models import PaymentIntentDB, SplitPaymentDB

bp = Blueprint("payments", __name__, url_prefix="/payments")


# ==================== PAYMENT INTENTS ====================

@bp.route("/intent", methods=["POST"])
@jwt_required()
def create_intent():
    """
    Create a new payment intent.
    
    Request body:
    {
        "amount": "100.00",
        "currency": "USDC",
        "description": "Payment for expense split",
        "event_id": "optional_event_id",
        "expense_id": "optional_expense_id",
        "type": "CONDITIONAL",  // optional, default CONDITIONAL
        "settlement_method": "OFF_RAMP_MOCK"  // optional
    }
    
    Response:
    {
        "intent": { ... payment intent data ... },
        "payment_url": "https://pay.fmm.finternetlab.io/?intent=xxx",
        "local_id": "mongodb_id"
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    # Validate required fields
    amount = data.get("amount")
    if not amount:
        return jsonify({"error": "Amount is required"}), 400
    
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400
    
    # Create Finternet payment intent
    finternet = FinternetService()
    
    intent_response = finternet.create_payment_intent(
        amount=str(amount),
        currency=data.get("currency", "USDC"),
        payment_type=data.get("type", "CONDITIONAL"),
        settlement_method=data.get("settlement_method", "OFF_RAMP_MOCK"),
        settlement_destination=data.get("settlement_destination", "bank_account_default"),
        description=data.get("description"),
        metadata={
            "user_id": user_id,
            "event_id": data.get("event_id"),
            "expense_id": data.get("expense_id")
        }
    )
    
    # Check for API errors
    if "error" in intent_response:
        return jsonify({
            "error": intent_response["error"].get("message", "Failed to create payment intent"),
            "details": intent_response["error"]
        }), 500
    
    # Store locally
    local_id = PaymentIntentDB.create(intent_response)
    
    # Update with user/event/expense IDs
    mongo.payment_intents.update_one(
        {"_id": ObjectId(local_id)},
        {"$set": {
            "user_id": user_id,
            "event_id": data.get("event_id"),
            "expense_id": data.get("expense_id")
        }}
    )
    
    payment_url = finternet.get_payment_url(intent_response)
    
    return jsonify({
        "intent": intent_response,
        "payment_url": payment_url,
        "local_id": local_id
    }), 201


@bp.route("/intent/<intent_id>", methods=["GET"])
@jwt_required()
def get_intent(intent_id):
    """
    Get payment intent details.
    
    Fetches from Finternet API and updates local status.
    
    Path params:
    - intent_id: Finternet intent ID (intent_xxx) or local MongoDB ID
    
    Response:
    {
        "intent": { ... payment intent data ... },
        "local": { ... local database record ... }
    }
    """
    finternet = FinternetService()
    
    # Check if it's a local ID or Finternet ID
    if intent_id.startswith("intent_"):
        finternet_id = intent_id
        local_record = PaymentIntentDB.find_by_finternet_id(finternet_id)
    else:
        local_record = PaymentIntentDB.find_by_id(intent_id)
        finternet_id = local_record.get("finternet_id") if local_record else None
    
    if not finternet_id:
        return jsonify({"error": "Payment intent not found"}), 404
    
    # Fetch latest from Finternet
    intent_response = finternet.get_payment_intent(finternet_id)
    
    if "error" in intent_response:
        # Return local record if API fails
        if local_record:
            return jsonify({
                "intent": None,
                "local": local_record,
                "api_error": intent_response["error"]
            })
        return jsonify({"error": "Payment intent not found"}), 404
    
    # Update local status
    new_status = intent_response.get("status")
    if new_status and local_record:
        extra_data = {}
        if intent_response.get("data", {}).get("transactionHash"):
            extra_data["transaction_hash"] = intent_response["data"]["transactionHash"]
        if intent_response.get("data", {}).get("settlementStatus"):
            extra_data["settlement_status"] = intent_response["data"]["settlementStatus"]
        
        PaymentIntentDB.update_status(finternet_id, new_status, extra_data)
        local_record = PaymentIntentDB.find_by_finternet_id(finternet_id)
    
    return jsonify({
        "intent": intent_response,
        "local": local_record
    })


@bp.route("/intent/<intent_id>/confirm", methods=["POST"])
@jwt_required()
def confirm_intent(intent_id):
    """
    Confirm a payment intent with wallet signature.
    
    Request body:
    {
        "signature": "0x...",  // EIP-712 signature
        "payer_address": "0x..."  // Wallet address
    }
    
    Response:
    {
        "intent": { ... updated payment intent ... },
        "status": "PROCESSING"
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    signature = data.get("signature")
    payer_address = data.get("payer_address") or data.get("payerAddress")
    
    if not signature or not payer_address:
        return jsonify({"error": "signature and payer_address are required"}), 400
    
    # Determine Finternet ID
    if intent_id.startswith("intent_"):
        finternet_id = intent_id
    else:
        local_record = PaymentIntentDB.find_by_id(intent_id)
        finternet_id = local_record.get("finternet_id") if local_record else None
    
    if not finternet_id:
        return jsonify({"error": "Payment intent not found"}), 404
    
    # Confirm with Finternet
    finternet = FinternetService()
    confirm_response = finternet.confirm_payment(finternet_id, signature, payer_address)
    
    if "error" in confirm_response:
        return jsonify({
            "error": confirm_response["error"].get("message", "Failed to confirm payment"),
            "details": confirm_response["error"]
        }), 400
    
    # Update local record
    tx_hash = confirm_response.get("data", {}).get("transactionHash")
    PaymentIntentDB.confirm(finternet_id, signature, payer_address, tx_hash)
    
    # Update user's wallet address if not set
    mongo.users.update_one(
        {"_id": ObjectId(user_id), "wallet_address": None},
        {"$set": {"wallet_address": payer_address}}
    )
    
    return jsonify({
        "intent": confirm_response,
        "status": confirm_response.get("status", "PROCESSING")
    })


@bp.route("/intent/<intent_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_intent(intent_id):
    """
    Cancel a payment intent.
    
    Only works for intents in INITIATED or REQUIRES_SIGNATURE status.
    """
    if intent_id.startswith("intent_"):
        finternet_id = intent_id
    else:
        local_record = PaymentIntentDB.find_by_id(intent_id)
        finternet_id = local_record.get("finternet_id") if local_record else None
    
    if not finternet_id:
        return jsonify({"error": "Payment intent not found"}), 404
    
    finternet = FinternetService()
    cancel_response = finternet.cancel_payment(finternet_id)
    
    if "error" in cancel_response:
        return jsonify({
            "error": cancel_response["error"].get("message", "Failed to cancel payment"),
            "details": cancel_response["error"]
        }), 400
    
    # Update local status
    PaymentIntentDB.update_status(finternet_id, "CANCELLED")
    
    return jsonify({
        "intent": cancel_response,
        "status": "CANCELLED"
    })


# ==================== USER PAYMENTS ====================

@bp.route("/pending", methods=["GET"])
@jwt_required()
def get_pending_payments():
    """
    Get all pending payments for the current user.
    
    Returns split payments the user needs to pay.
    """
    user_id = get_jwt_identity()
    
    pending = SplitPaymentDB.find_pending_for_user(user_id)
    
    # Enrich with expense details
    for payment in pending:
        expense = mongo.expenses.find_one({"_id": ObjectId(payment["expense_id"])})
        if expense:
            payment["expense_description"] = expense.get("description", "Expense")
            payment["expense_amount"] = expense.get("amount", 0)
            
            # Get event name
            event = mongo.events.find_one({"_id": expense.get("event_id")})
            if event:
                payment["event_name"] = event.get("name", "Event")
    
    return jsonify({"pending_payments": pending})


@bp.route("/history", methods=["GET"])
@jwt_required()
def get_payment_history():
    """
    Get payment history for the current user.
    """
    user_id = get_jwt_identity()
    limit = request.args.get("limit", 20, type=int)
    
    payments = PaymentIntentDB.find_by_user(user_id, limit)
    
    return jsonify({"payments": payments})


# ==================== CONDITIONAL PAYMENTS (ESCROW) ====================

@bp.route("/intent/<intent_id>/escrow", methods=["GET"])
@jwt_required()
def get_escrow(intent_id):
    """
    Get conditional payment (escrow) details.
    
    Only available for DELIVERY_VS_PAYMENT type payments.
    """
    if intent_id.startswith("intent_"):
        finternet_id = intent_id
    else:
        local_record = PaymentIntentDB.find_by_id(intent_id)
        finternet_id = local_record.get("finternet_id") if local_record else None
    
    if not finternet_id:
        return jsonify({"error": "Payment intent not found"}), 404
    
    finternet = FinternetService()
    escrow_response = finternet.get_conditional_payment(finternet_id)
    
    if "error" in escrow_response:
        return jsonify({
            "error": escrow_response["error"].get("message", "Failed to get escrow details"),
            "details": escrow_response["error"]
        }), 400
    
    return jsonify({"escrow": escrow_response})


@bp.route("/intent/<intent_id>/escrow/delivery-proof", methods=["POST"])
@jwt_required()
def submit_delivery_proof(intent_id):
    """
    Submit delivery proof for conditional payment.
    
    Request body:
    {
        "proof_hash": "0x...",  // Keccak256 hash of proof
        "proof_uri": "https://...",  // Optional URI to proof
        "submitted_by": "0x..."  // Wallet address
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    proof_hash = data.get("proof_hash") or data.get("proofHash")
    submitted_by = data.get("submitted_by") or data.get("submittedBy")
    
    if not proof_hash or not submitted_by:
        return jsonify({"error": "proof_hash and submitted_by are required"}), 400
    
    if intent_id.startswith("intent_"):
        finternet_id = intent_id
    else:
        local_record = PaymentIntentDB.find_by_id(intent_id)
        finternet_id = local_record.get("finternet_id") if local_record else None
    
    if not finternet_id:
        return jsonify({"error": "Payment intent not found"}), 404
    
    finternet = FinternetService()
    proof_response = finternet.submit_delivery_proof(
        finternet_id,
        proof_hash,
        submitted_by,
        proof_uri=data.get("proof_uri") or data.get("proofURI")
    )
    
    if "error" in proof_response:
        return jsonify({
            "error": proof_response["error"].get("message", "Failed to submit delivery proof"),
            "details": proof_response["error"]
        }), 400
    
    return jsonify({"delivery_proof": proof_response})


@bp.route("/intent/<intent_id>/escrow/dispute", methods=["POST"])
@jwt_required()
def raise_dispute(intent_id):
    """
    Raise a dispute for conditional payment.
    
    Request body:
    {
        "reason": "Item not delivered as described",
        "raised_by": "0x...",  // Wallet address
        "dispute_window": "604800"  // Optional, default 7 days
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    reason = data.get("reason")
    raised_by = data.get("raised_by") or data.get("raisedBy")
    
    if not reason or not raised_by:
        return jsonify({"error": "reason and raised_by are required"}), 400
    
    if intent_id.startswith("intent_"):
        finternet_id = intent_id
    else:
        local_record = PaymentIntentDB.find_by_id(intent_id)
        finternet_id = local_record.get("finternet_id") if local_record else None
    
    if not finternet_id:
        return jsonify({"error": "Payment intent not found"}), 404
    
    finternet = FinternetService()
    dispute_response = finternet.raise_dispute(
        finternet_id,
        reason,
        raised_by,
        dispute_window=data.get("dispute_window", "604800")
    )
    
    if "error" in dispute_response:
        return jsonify({
            "error": dispute_response["error"].get("message", "Failed to raise dispute"),
            "details": dispute_response["error"]
        }), 400
    
    return jsonify({"dispute": dispute_response})


# ==================== DEPOSIT CONFIRMATION ====================

@bp.route("/deposit/confirm", methods=["POST"])
@jwt_required()
def confirm_deposit():
    """
    Confirm a deposit payment after Finternet transaction is complete.
    
    This is called after the user signs the transaction on Finternet.
    Updates the participant's balance and event total.
    
    Request body:
    {
        "intent_id": "local_mongodb_id or finternet_id",
        "signature": "0x...",  // Optional, if confirming directly
        "payer_address": "0x..."
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    intent_id = data.get("intent_id")
    if not intent_id:
        return jsonify({"error": "intent_id is required"}), 400
    
    # Find the payment intent
    if intent_id.startswith("intent_"):
        finternet_id = intent_id
        local_record = PaymentIntentDB.find_by_finternet_id(finternet_id)
    else:
        local_record = PaymentIntentDB.find_by_id(intent_id)
        finternet_id = local_record.get("finternet_id") if local_record else None
    
    if not local_record:
        return jsonify({"error": "Payment intent not found"}), 404
    
    # Verify this is a deposit intent
    if local_record.get("intent_type") != "deposit":
        return jsonify({"error": "This is not a deposit payment intent"}), 400
    
    # Verify user owns this intent
    if local_record.get("user_id") != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Check if already confirmed
    if local_record.get("status") in ["SUCCEEDED", "SETTLED", "FINAL"]:
        return jsonify({
            "message": "Deposit already confirmed",
            "status": local_record.get("status")
        })
    
    finternet = FinternetService()
    
    # Check status with Finternet
    intent_response = finternet.get_payment_intent(finternet_id)
    status = intent_response.get("status")
    
    # If still initiated and we have signature, confirm it
    if status == "INITIATED" and data.get("signature") and data.get("payer_address"):
        confirm_response = finternet.confirm_payment(
            finternet_id,
            data["signature"],
            data["payer_address"]
        )
        if "error" in confirm_response:
            return jsonify({
                "error": confirm_response["error"].get("message", "Failed to confirm payment"),
                "details": confirm_response["error"]
            }), 400
        status = confirm_response.get("status", "PROCESSING")
    
    # Check if payment succeeded
    if status in ["SUCCEEDED", "SETTLED", "FINAL"]:
        # Update local record
        PaymentIntentDB.update_status(finternet_id, status)
        
        # Update participant balance
        event_id = local_record.get("event_id")
        amount = float(local_record.get("amount", 0))
        
        if event_id:
            event_oid = ObjectId(event_id)
            user_oid = ObjectId(user_id)
            
            # Update participant
            mongo.participants.update_one(
                {"event_id": event_oid, "user_id": user_oid},
                {"$inc": {
                    "deposit_amount": amount,
                    "balance": amount
                }}
            )
            
            # Update event total
            mongo.events.update_one(
                {"_id": event_oid},
                {"$inc": {"total_pool": amount}}
            )
            
            # Update activity to confirmed
            mongo.activities.update_one(
                {"payment_intent_id": str(local_record["_id"])},
                {"$set": {
                    "type": "deposit",
                    "description": "Deposit confirmed"
                }}
            )
            
            # Log confirmed deposit
            mongo.activities.insert_one({
                "type": "deposit",
                "event_id": event_oid,
                "user_id": user_oid,
                "amount": amount,
                "description": "Deposit (via Finternet)",
                "payment_intent_id": str(local_record["_id"]),
                "created_at": datetime.utcnow()
            })
        
        return jsonify({
            "message": "Deposit confirmed",
            "amount": amount,
            "status": status
        })
    
    # Payment still processing
    return jsonify({
        "message": "Payment still processing",
        "status": status,
        "finternet_id": finternet_id
    }), 202


@bp.route("/webhook", methods=["POST"])
def finternet_webhook():
    """
    Webhook endpoint for Finternet payment status updates.
    
    This is called by Finternet when payment status changes.
    Automatically confirms deposits and refunds.
    """
    data = request.get_json() or {}
    
    # Verify webhook (in production, verify signature)
    # webhook_secret = os.environ.get("FINTERNET_WEBHOOK_SECRET")
    
    event_type = data.get("type")
    intent_data = data.get("data", {})
    finternet_id = intent_data.get("id")
    
    if not finternet_id:
        return jsonify({"error": "Missing intent ID"}), 400
    
    # Find local record
    local_record = PaymentIntentDB.find_by_finternet_id(finternet_id)
    if not local_record:
        return jsonify({"error": "Unknown payment intent"}), 404
    
    new_status = intent_data.get("status")
    if new_status:
        PaymentIntentDB.update_status(finternet_id, new_status)
    
    # Handle successful payments
    if new_status in ["SUCCEEDED", "SETTLED", "FINAL"]:
        intent_type = local_record.get("intent_type")
        
        if intent_type == "deposit":
            # Auto-confirm deposit
            event_id = local_record.get("event_id")
            user_id = local_record.get("user_id")
            amount = float(local_record.get("amount", 0))
            
            if event_id and user_id:
                event_oid = ObjectId(event_id)
                user_oid = ObjectId(user_id)
                
                mongo.participants.update_one(
                    {"event_id": event_oid, "user_id": user_oid},
                    {"$inc": {
                        "deposit_amount": amount,
                        "balance": amount
                    }}
                )
                
                mongo.events.update_one(
                    {"_id": event_oid},
                    {"$inc": {"total_pool": amount}}
                )
                
                mongo.activities.insert_one({
                    "type": "deposit",
                    "event_id": event_oid,
                    "user_id": user_oid,
                    "amount": amount,
                    "description": "Deposit confirmed (webhook)",
                    "created_at": datetime.utcnow()
                })
        
        elif intent_type == "refund":
            # Auto-confirm refund
            event_id = local_record.get("event_id")
            user_id = local_record.get("user_id")
            
            if event_id and user_id:
                event_oid = ObjectId(event_id)
                user_oid = ObjectId(user_id)
                
                # Update refund record
                mongo.refunds.update_one(
                    {"finternet_id": finternet_id},
                    {"$set": {
                        "status": "completed",
                        "completed_at": datetime.utcnow()
                    }}
                )
                
                # Zero out balance
                mongo.participants.update_one(
                    {"event_id": event_oid, "user_id": user_oid},
                    {"$set": {"balance": 0}}
                )
                
                mongo.activities.insert_one({
                    "type": "refund_completed",
                    "event_id": event_oid,
                    "user_id": user_oid,
                    "amount": float(local_record.get("amount", 0)),
                    "description": "Refund completed (webhook)",
                    "created_at": datetime.utcnow()
                })
    
    return jsonify({"received": True})
