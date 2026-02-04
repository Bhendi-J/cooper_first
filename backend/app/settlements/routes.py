"""
Settlement routes for finalizing events and processing refunds.

Endpoints:
- POST /settlements/finalize/<event_id> - Finalize an event and calculate balances
- GET /settlements/<event_id>/summary - Get settlement summary for an event
- POST /settlements/<event_id>/refund - Request refund for remaining balance
- GET /settlements/refunds - Get user's refund history
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId, errors
from datetime import datetime

from app.extensions import db as mongo
from app.payments.services.finternet import FinternetService
from app.payments.models import PaymentIntentDB

bp = Blueprint("settlements", __name__, url_prefix="/settlements")


def safe_object_id(value):
    try:
        return ObjectId(value)
    except errors.InvalidId:
        return None


@bp.route("/finalize/<event_id>", methods=["POST"])
@jwt_required()
def finalize(event_id):
    """
    Finalize an event - calculates final balances and enables refunds.
    
    Only the event creator can finalize.
    Changes event status to 'completed'.
    """
    user_id = safe_object_id(get_jwt_identity())
    event_oid = safe_object_id(event_id)
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Only creator can finalize
    if event["creator_id"] != user_id:
        return jsonify({"error": "Only the event creator can finalize"}), 403
    
    if event["status"] == "completed":
        return jsonify({"error": "Event already finalized"}), 400
    
    # Get all participants with their balances
    participants = list(mongo.participants.find({"event_id": event_oid}))
    
    # Calculate settlement summary
    settlements = []
    total_refundable = 0
    
    for p in participants:
        user = mongo.users.find_one({"_id": p["user_id"]})
        balance = p.get("balance", 0)
        
        if balance > 0:
            total_refundable += balance
        
        settlements.append({
            "user_id": str(p["user_id"]),
            "user_name": user.get("name") if user else "Unknown",
            "deposited": p.get("deposit_amount", 0),
            "spent": p.get("total_spent", 0),
            "balance": balance,
            "status": "refund_available" if balance > 0 else "settled"
        })
    
    # Update event status
    mongo.events.update_one(
        {"_id": event_oid},
        {
            "$set": {
                "status": "completed",
                "finalized_at": datetime.utcnow(),
                "finalized_by": user_id
            }
        }
    )
    
    # Log activity
    mongo.activities.insert_one({
        "type": "event_finalized",
        "event_id": event_oid,
        "user_id": user_id,
        "description": f"Event '{event.get('name')}' was finalized",
        "created_at": datetime.utcnow()
    })
    
    return jsonify({
        "event_id": event_id,
        "status": "completed",
        "settlements": settlements,
        "total_refundable": total_refundable
    })


@bp.route("/<event_id>/summary", methods=["GET"])
@jwt_required()
def get_summary(event_id):
    """
    Get settlement summary for an event.
    Shows each participant's balance and refund status.
    """
    user_id = safe_object_id(get_jwt_identity())
    event_oid = safe_object_id(event_id)
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Check if user is participant
    participant = mongo.participants.find_one({
        "event_id": event_oid,
        "user_id": user_id
    })
    if not participant:
        return jsonify({"error": "Not a participant"}), 403
    
    # Get all participants
    participants = list(mongo.participants.find({"event_id": event_oid}))
    
    settlements = []
    for p in participants:
        user = mongo.users.find_one({"_id": p["user_id"]})
        
        # Check for pending refunds
        pending_refund = mongo.refunds.find_one({
            "event_id": event_oid,
            "user_id": p["user_id"],
            "status": {"$in": ["pending", "processing"]}
        })
        
        settlements.append({
            "user_id": str(p["user_id"]),
            "user_name": user.get("name") if user else "Unknown",
            "deposited": p.get("deposit_amount", 0),
            "spent": p.get("total_spent", 0),
            "balance": p.get("balance", 0),
            "refund_pending": pending_refund is not None,
            "is_you": p["user_id"] == user_id
        })
    
    return jsonify({
        "event_id": event_id,
        "event_name": event.get("name"),
        "event_status": event.get("status"),
        "total_pool": event.get("total_pool", 0),
        "total_spent": event.get("total_spent", 0),
        "settlements": settlements
    })


@bp.route("/<event_id>/refund", methods=["POST"])
@jwt_required()
def request_refund(event_id):
    """
    Request a refund for remaining balance after event is finalized.
    
    Request body (optional):
    {
        "wallet_address": "0x...",  // Wallet to receive refund
        "use_finternet": true  // Use Finternet for refund (default true)
    }
    
    Returns payment intent for the refund.
    """
    user_id = safe_object_id(get_jwt_identity())
    event_oid = safe_object_id(event_id)
    data = request.get_json() or {}
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Event must be completed to request refund
    if event["status"] != "completed":
        return jsonify({"error": "Event must be finalized before requesting refunds"}), 400
    
    # Get participant balance
    participant = mongo.participants.find_one({
        "event_id": event_oid,
        "user_id": user_id
    })
    if not participant:
        return jsonify({"error": "Not a participant"}), 403
    
    balance = participant.get("balance", 0)
    if balance <= 0:
        return jsonify({"error": "No balance available for refund"}), 400
    
    # Check for existing pending refund
    existing_refund = mongo.refunds.find_one({
        "event_id": event_oid,
        "user_id": user_id,
        "status": {"$in": ["pending", "processing"]}
    })
    if existing_refund:
        return jsonify({
            "error": "Refund already in progress",
            "refund_id": str(existing_refund["_id"]),
            "status": existing_refund["status"]
        }), 400
    
    use_finternet = data.get("use_finternet", True)
    user = mongo.users.find_one({"_id": user_id})
    wallet_address = data.get("wallet_address") or user.get("wallet_address")
    
    # Create refund record
    refund = {
        "event_id": event_oid,
        "user_id": user_id,
        "amount": balance,
        "wallet_address": wallet_address,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    if use_finternet:
        # Create Finternet payment intent for refund
        finternet = FinternetService()
        
        intent_response = finternet.create_payment_intent(
            amount=str(balance),
            currency="USDC",
            payment_type="CONDITIONAL",
            settlement_method="OFF_RAMP_MOCK",
            description=f"Refund from event: {event.get('name', 'Event')}",
            metadata={
                "user_id": str(user_id),
                "event_id": str(event_oid),
                "type": "refund"
            }
        )
        
        if "error" in intent_response:
            return jsonify({
                "error": intent_response["error"].get("message", "Failed to create refund payment"),
                "details": intent_response["error"]
            }), 500
        
        # Store payment intent
        local_id = PaymentIntentDB.create(intent_response)
        
        mongo.payment_intents.update_one(
            {"_id": ObjectId(local_id)},
            {"$set": {
                "user_id": str(user_id),
                "event_id": str(event_oid),
                "intent_type": "refund"
            }}
        )
        
        refund["payment_intent_id"] = local_id
        refund["finternet_id"] = intent_response.get("id")
        
        payment_url = finternet.get_payment_url(intent_response)
    else:
        payment_url = None
    
    # Insert refund record
    result = mongo.refunds.insert_one(refund)
    
    # Log activity
    mongo.activities.insert_one({
        "type": "refund_requested",
        "event_id": event_oid,
        "user_id": user_id,
        "amount": balance,
        "description": f"Refund requested: ${balance:.2f}",
        "created_at": datetime.utcnow()
    })
    
    response = {
        "refund_id": str(result.inserted_id),
        "amount": balance,
        "status": "pending"
    }
    
    if use_finternet:
        response["payment_url"] = payment_url
        response["intent_id"] = local_id
        response["finternet_id"] = intent_response.get("id")
    
    return jsonify(response)


@bp.route("/<event_id>/refund/confirm", methods=["POST"])
@jwt_required()
def confirm_refund(event_id):
    """
    Confirm a refund after Finternet payment is complete.
    
    This is called after the user has signed the transaction on Finternet.
    
    Request body:
    {
        "refund_id": "xxx",
        "signature": "0x...",  // Optional, if confirming directly
        "payer_address": "0x..."
    }
    """
    user_id = safe_object_id(get_jwt_identity())
    event_oid = safe_object_id(event_id)
    data = request.get_json() or {}
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    refund_id = data.get("refund_id")
    if not refund_id:
        return jsonify({"error": "refund_id is required"}), 400
    
    refund = mongo.refunds.find_one({
        "_id": safe_object_id(refund_id),
        "event_id": event_oid,
        "user_id": user_id
    })
    
    if not refund:
        return jsonify({"error": "Refund not found"}), 404
    
    if refund["status"] == "completed":
        return jsonify({"error": "Refund already completed"}), 400
    
    # If we have a Finternet intent, check/confirm it
    if refund.get("finternet_id"):
        finternet = FinternetService()
        
        # Check status
        intent = finternet.get_payment_intent(refund["finternet_id"])
        status = intent.get("status")
        
        if status in ["SUCCEEDED", "SETTLED", "FINAL"]:
            # Refund is complete
            pass
        elif status == "INITIATED" and data.get("signature"):
            # Confirm with signature
            confirm_response = finternet.confirm_payment(
                refund["finternet_id"],
                data["signature"],
                data.get("payer_address")
            )
            if "error" in confirm_response:
                return jsonify({
                    "error": confirm_response["error"].get("message", "Failed to confirm refund"),
                    "details": confirm_response["error"]
                }), 400
        else:
            return jsonify({
                "error": "Refund payment not yet completed",
                "status": status
            }), 400
    
    # Update refund status
    mongo.refunds.update_one(
        {"_id": refund["_id"]},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.utcnow()
        }}
    )
    
    # Update participant balance to 0
    mongo.participants.update_one(
        {"event_id": event_oid, "user_id": user_id},
        {"$set": {"balance": 0}}
    )
    
    # Log activity
    mongo.activities.insert_one({
        "type": "refund_completed",
        "event_id": event_oid,
        "user_id": user_id,
        "amount": refund["amount"],
        "description": f"Refund completed: ${refund['amount']:.2f}",
        "created_at": datetime.utcnow()
    })
    
    return jsonify({
        "refund_id": str(refund["_id"]),
        "amount": refund["amount"],
        "status": "completed"
    })


@bp.route("/refunds", methods=["GET"])
@jwt_required()
def get_user_refunds():
    """
    Get all refunds for the current user.
    """
    user_id = safe_object_id(get_jwt_identity())
    
    refunds = list(mongo.refunds.find({"user_id": user_id}).sort("created_at", -1))
    
    result = []
    for r in refunds:
        event = mongo.events.find_one({"_id": r["event_id"]})
        result.append({
            "_id": str(r["_id"]),
            "event_id": str(r["event_id"]),
            "event_name": event.get("name") if event else "Unknown",
            "amount": r["amount"],
            "status": r["status"],
            "payment_url": None,  # Could fetch from Finternet if pending
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "completed_at": r["completed_at"].isoformat() if r.get("completed_at") else None
        })
    
    return jsonify({"refunds": result})
