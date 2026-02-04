"""Payment routes for Finternet integration."""

from app.payments.services.finternet import FinternetService
import os
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

bp = Blueprint("payments", __name__)


# ==================== PAYMENT INTENTS ====================

@bp.route("/intent", methods=["POST"])
@jwt_required()
def create_intent():
    """
    Create a new payment intent via Finternet.
    Create a new payment intent.
    
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
    
    currency = data.get("currency", "USDC")
    description = data.get("description", "Cooper payment")
    
    try:
        finternet = FinternetService()
        result = finternet.create_payment_intent(
            amount=str(amount),
            currency=currency,
            description=description
        )
        
        # Extract key info for frontend
        intent_data = result.get("data", result)
        response = {
            "id": intent_data.get("id"),
            "status": intent_data.get("status"),
            "paymentUrl": intent_data.get("paymentUrl"),
            "amount": intent_data.get("amount"),
            "currency": intent_data.get("currency", currency)
        }
        
        return jsonify(response), 201
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to create payment intent: {str(e)}"}), 500
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
    This endpoint instantly marks a payment as SUCCEEDED.
    """
    try:
        finternet = FinternetService()
        # Force success status
        result = finternet.confirm_payment(
            intent_id,
            signature="0xdemo_signature",
            payer_address="0xdemo_payer"
        )
        
        intent_data = result.get("data", result)
        response = {
            "id": intent_data.get("id", intent_id),
            "status": "SUCCEEDED",
            "transactionHash": intent_data.get("transactionHash"),
            "message": "Payment simulated successfully for demo"
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Failed to simulate payment: {str(e)}"}), 500
