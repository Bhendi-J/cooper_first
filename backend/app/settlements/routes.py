"""Settlement routes for Splitwise-style expense settling."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.settlements.services import SettlementCalculator
from app.core import DebtService, NotificationService, ReliabilityService
from app.extensions import db as mongo
from bson import ObjectId
from datetime import datetime

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
    Also settles any outstanding debts.
    
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
        amount = float(amount)
        
        # Record the settlement
        settlement = SettlementCalculator.record_settlement(
            event_id=event_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            payment_method=payment_method
        )
        
        # Also settle any outstanding debts for this user in this event
        debts_settled = []
        user_debts = DebtService.get_user_debts(from_user_id, event_id)
        
        remaining_amount = amount
        for debt in user_debts:
            if remaining_amount <= 0:
                break
            
            debt_amount = debt.get("remaining_amount", debt.get("amount", 0))
            settle_amount = min(remaining_amount, debt_amount)
            
            if settle_amount > 0:
                result = DebtService.settle_debt(
                    debt_id=str(debt["_id"]),
                    amount=settle_amount,
                    payment_reference=settlement.get("_id")
                )
                
                if result.get("success"):
                    debts_settled.append({
                        "debt_id": str(debt["_id"]),
                        "amount_settled": settle_amount,
                        "status": result.get("new_status")
                    })
                    
                    # Notify about debt settlement
                    if result.get("new_status") == "settled":
                        NotificationService.notify_debt_settled(
                            user_id=from_user_id,
                            amount=debt.get("amount", 0),
                            event_id=event_id
                        )
                
                remaining_amount -= settle_amount
        
        # Update reliability score
        ReliabilityService.calculate_reliability_score(from_user_id)
        
        return jsonify({
            "settlement": settlement,
            "debts_settled": debts_settled if debts_settled else None
        }), 201
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


# ------------------ DEBT ENDPOINTS ------------------

@bp.route("/debts/my", methods=["GET"])
@jwt_required()
def get_my_debts():
    """Get all outstanding debts for current user."""
    user_id = get_jwt_identity()
    
    debts = DebtService.get_user_debts(user_id)
    
    # Check for restrictions
    restrictions = DebtService.check_debt_restrictions(user_id)
    
    return jsonify({
        "debts": debts,
        "restrictions": restrictions
    })


@bp.route("/debts/<debt_id>/settle", methods=["POST"])
@jwt_required()
def settle_specific_debt(debt_id):
    """Settle a specific debt (creates payment intent)."""
    from app.payments.services.finternet import FinternetService
    
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    debt = mongo.debts.find_one({
        "_id": ObjectId(debt_id),
        "user_id": ObjectId(user_id),
        "status": {"$in": ["outstanding", "partially_paid"]}
    })
    
    if not debt:
        return jsonify({"error": "Debt not found or already settled"}), 404
    
    amount = data.get("amount", debt.get("remaining_amount", debt.get("amount")))
    
    try:
        finternet = FinternetService()
        result = finternet.create_payment_intent(
            amount=str(amount),
            currency="USDC",
            description=f"Debt settlement"
        )
        
        intent_data = result.get("data", result)
        intent_id = intent_data.get("id")
        
        # Store payment tracking
        mongo.payment_tracking.insert_one({
            "intent_id": intent_id,
            "user_id": ObjectId(user_id),
            "debt_id": ObjectId(debt_id),
            "purpose": "debt_settlement",
            "amount": float(amount),
            "status": "initiated",
            "created_at": datetime.utcnow()
        })
        
        return jsonify({
            "id": intent_id,
            "status": intent_data.get("status"),
            "paymentUrl": intent_data.get("paymentUrl"),
            "amount": amount,
            "debt_id": debt_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/debts/<debt_id>/forgive", methods=["POST"])
@jwt_required()
def forgive_debt(debt_id):
    """Forgive a debt (creditor only - event creator)."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    debt = mongo.debts.find_one({"_id": ObjectId(debt_id)})
    if not debt:
        return jsonify({"error": "Debt not found"}), 404
    
    # Only event creator can forgive
    event = mongo.events.find_one({"_id": debt.get("event_id")})
    if not event or str(event["creator_id"]) != user_id:
        return jsonify({"error": "Only event creator can forgive debts"}), 403
    
    result = DebtService.forgive_debt(
        debt_id=debt_id,
        forgiven_by=user_id,
        reason=data.get("reason", "")
    )
    
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400
    
    # Notify debtor
    NotificationService.notify_debt_settled(
        user_id=str(debt["user_id"]),
        amount=debt.get("amount", 0),
        event_id=str(debt.get("event_id"))
    )
    
    return jsonify({
        "message": "Debt forgiven",
        "debt_id": debt_id
    })


# ------------------ NOTIFICATION ENDPOINTS ------------------

@bp.route("/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    """Get notifications for current user."""
    user_id = get_jwt_identity()
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = int(request.args.get("limit", 50))
    
    notifications = NotificationService.get_user_notifications(
        user_id=user_id,
        unread_only=unread_only,
        limit=limit
    )
    
    unread_count = NotificationService.get_unread_count(user_id)
    
    return jsonify({
        "notifications": notifications,
        "unread_count": unread_count
    })


@bp.route("/notifications/<notification_id>/read", methods=["POST"])
@jwt_required()
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    success = NotificationService.mark_as_read(notification_id)
    
    return jsonify({
        "success": success
    })


@bp.route("/notifications/read-all", methods=["POST"])
@jwt_required()
def mark_all_notifications_read():
    """Mark all notifications as read."""
    user_id = get_jwt_identity()
    
    count = NotificationService.mark_all_as_read(user_id)
    
    return jsonify({
        "marked_read": count
    })


# ------------------ RELIABILITY ENDPOINTS ------------------

@bp.route("/reliability/score", methods=["GET"])
@jwt_required()
def get_reliability_score():
    """Get reliability score for current user."""
    user_id = get_jwt_identity()
    
    score_data = ReliabilityService.calculate_reliability_score(user_id)
    
    # Get tier restrictions
    tier = score_data.get("tier", "good")
    restrictions = ReliabilityService.get_tier_restrictions(tier)
    
    return jsonify({
        "score": score_data.get("score", 0),
        "tier": tier,
        "factors": score_data.get("factors", {}),
        "restrictions": restrictions
    })
