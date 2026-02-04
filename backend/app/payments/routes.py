"""Payment routes for Finternet integration."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.payments.services.finternet import FinternetService
import os

bp = Blueprint("payments", __name__)


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