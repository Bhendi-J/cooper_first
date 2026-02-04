"""Settlement routes for Splitwise-style expense settling."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.settlements.services import SettlementCalculator

bp = Blueprint("settlements", __name__, url_prefix="/settlements")


@bp.route("/balances/<event_id>", methods=["GET"])
@jwt_required()
def get_balances(event_id):
    """
    Get all participant balances for an event.
    
    Returns:
    {
        "balances": [
            {"user_id": "...", "username": "alice", "balance": 50.00},
            {"user_id": "...", "username": "bob", "balance": -30.00},
        ]
    }
    
    Positive balance = is owed money
    Negative balance = owes money
    """
    try:
        balances = SettlementCalculator.get_balances(event_id)
        return jsonify({"balances": balances})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/debts/<event_id>", methods=["GET"])
@jwt_required()
def get_debts(event_id):
    """
    Calculate who owes whom using Splitwise-style algorithm.
    Minimizes the number of transactions needed.
    
    Returns:
    {
        "debts": [
            {"from_user": "...", "from_username": "bob", "to_user": "...", "to_username": "alice", "amount": 30.00}
        ],
        "total_owed": 50.00
    }
    """
    try:
        debts = SettlementCalculator.calculate_debts(event_id)
        total_owed = sum(d["amount"] for d in debts)
        return jsonify({
            "debts": debts,
            "total_owed": round(total_owed, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/settle", methods=["POST"])
@jwt_required()
def record_settlement():
    """
    Record a settlement payment between two users.
    
    Request body:
    {
        "event_id": "...",
        "from_user_id": "...",
        "to_user_id": "...",
        "amount": 30.00,
        "payment_method": "finternet"  // optional
    }
    """
    data = request.get_json() or {}
    
    event_id = data.get("event_id")
    from_user_id = data.get("from_user_id")
    to_user_id = data.get("to_user_id")
    amount = data.get("amount")
    payment_method = data.get("payment_method", "finternet")
    
    if not all([event_id, from_user_id, to_user_id, amount]):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        settlement = SettlementCalculator.record_settlement(
            event_id=event_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=float(amount),
            payment_method=payment_method
        )
        return jsonify({"settlement": settlement}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/history/<event_id>", methods=["GET"])
@jwt_required()
def get_history(event_id):
    """
    Get settlement history for an event.
    """
    try:
        history = SettlementCalculator.get_settlement_history(event_id)
        return jsonify({"settlements": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/finalize/<event_id>", methods=["POST"])
@jwt_required()
def finalize(event_id):
    """
    Finalize all settlements for an event.
    Marks the event as settled.
    """
    from app.extensions import db as mongo
    from bson import ObjectId
    
    try:
        # Check if all balances are zero
        balances = SettlementCalculator.get_balances(event_id)
        unsettled = [b for b in balances if abs(b["balance"]) > 0.01]
        
        if unsettled:
            return jsonify({
                "error": "Cannot finalize - some balances are not settled",
                "unsettled": unsettled
            }), 400
        
        # Mark event as settled
        mongo.events.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": {"status": "settled", "settled_at": __import__("datetime").datetime.utcnow()}}
        )
        
        return jsonify({
            "event_id": event_id,
            "status": "settled",
            "message": "All balances have been settled!"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
