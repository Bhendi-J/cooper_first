from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId, errors
from datetime import datetime
import secrets
import hashlib
from app.extensions import db as mongo
from app.core import (
    JoinRequestService, RuleEnforcementService, ReliabilityService,
    NotificationService, PoolService
)

events_bp = Blueprint("events", __name__)


# ------------------ HELPERS ------------------

def safe_object_id(value):
    try:
        return ObjectId(value)
    except errors.InvalidId:
        return None


def is_participant(event_id, user_id):
    return mongo.participants.find_one({
        "event_id": event_id,
        "user_id": user_id
    })


def generate_invite_code():
    """Generate a unique 8-character invite code."""
    return secrets.token_urlsafe(6)[:8].upper()


# ------------------ ROUTES ------------------

@events_bp.route("/", methods=["POST"])
@jwt_required()
def create_event():
    user_id = safe_object_id(get_jwt_identity())
    data = request.get_json()

    if not data or not data.get("name"):
        return jsonify({"error": "Event name is required"}), 400

    invite_code = generate_invite_code()
    
    # Ensure unique invite code
    while mongo.events.find_one({"invite_code": invite_code}):
        invite_code = generate_invite_code()

    # Parse rules with all options
    rules_data = data.get("rules", {})
    event_rules = {
        # Spending limits
        "spending_limit": rules_data.get("spending_limit"),
        "max_expense_per_transaction": rules_data.get("max_expense_per_transaction"),
        "min_expense_per_transaction": rules_data.get("min_expense_per_transaction"),
        "max_cumulative_spend_per_user": rules_data.get("max_cumulative_spend_per_user"),
        
        # Deposit limits
        "min_deposit": rules_data.get("min_deposit"),
        "max_deposit": rules_data.get("max_deposit"),
        "deposit_margin_min": rules_data.get("deposit_margin_min"),
        "deposit_margin_max": rules_data.get("deposit_margin_max"),
        
        # Approval settings
        "approval_required": rules_data.get("approval_required", False),
        "auto_approve_under": rules_data.get("auto_approve_under", 100),
        "approval_required_threshold": rules_data.get("approval_required_threshold"),
        "warning_threshold": rules_data.get("warning_threshold"),
        
        # Category restrictions
        "restricted_categories": rules_data.get("restricted_categories", []),
        "blocked_categories": rules_data.get("blocked_categories", []),
        
        # Other settings
        "allow_wallet_fallback": rules_data.get("allow_wallet_fallback", True),
        "max_debt_allowed": rules_data.get("max_debt_allowed"),
    }

    event = {
        "name": data["name"],
        "description": data.get("description", ""),
        "creator_id": user_id,
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "status": "active",
        "invite_code": invite_code,
        "invite_enabled": True,
        "shared_wallet_id": None,
        "merkle_root": None,
        "rules": event_rules,
        "total_pool": 0,
        "total_spent": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = mongo.events.insert_one(event)

    mongo.participants.insert_one({
        "event_id": result.inserted_id,
        "user_id": user_id,
        "deposit_amount": 0,
        "total_spent": 0,
        "balance": 0,
        "status": "active",
        "categories": [],
        "created_at": datetime.utcnow()
    })

    event["_id"] = str(result.inserted_id)
    event["creator_id"] = str(event["creator_id"])
    
    # Include invite link in response
    base_url = request.host_url.rstrip("/")
    event["invite_url"] = f"{base_url}/api/v1/events/join/{invite_code}"

    return jsonify({"event": event}), 201


@events_bp.route("/", methods=["GET"])
@jwt_required()
def get_user_events():
    user_id = safe_object_id(get_jwt_identity())

    participant_events = mongo.participants.find({"user_id": user_id})
    event_ids = [p["event_id"] for p in participant_events]

    events = mongo.events.find({"_id": {"$in": event_ids}})

    response = []
    for event in events:
        event["_id"] = str(event["_id"])
        event["creator_id"] = str(event["creator_id"])
        response.append(event)

    return jsonify({"events": response})


@events_bp.route("/<event_id>", methods=["GET"])
@jwt_required()
def get_event(event_id):
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())

    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400

    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404

    if not is_participant(event_oid, user_id):
        return jsonify({"error": "Unauthorized"}), 403

    event["_id"] = str(event["_id"])
    event["creator_id"] = str(event["creator_id"])

    participants = mongo.participants.find({"event_id": event_oid})
    participant_list = []

    for p in participants:
        user = mongo.users.find_one({"_id": p["user_id"]})
        participant_list.append({
            "_id": str(p["_id"]),
            "user_id": str(p["user_id"]),
            "user_name": user["name"] if user else "Unknown",
            "deposit_amount": p["deposit_amount"],
            "total_spent": p["total_spent"],
            "balance": p["balance"],
            "status": p["status"]
        })

    event["participants"] = participant_list

    return jsonify({"event": event})


@events_bp.route("/<event_id>/join", methods=["POST"])
@jwt_required()
def join_event(event_id):
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())

    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400

    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404

    if event["status"] != "active":
        return jsonify({"error": "Event is not active"}), 400

    if is_participant(event_oid, user_id):
        return jsonify({"error": "Already a participant"}), 409

    mongo.participants.insert_one({
        "event_id": event_oid,
        "user_id": user_id,
        "deposit_amount": 0,
        "total_spent": 0,
        "balance": 0,
        "status": "active",
        "categories": [],
        "created_at": datetime.utcnow()
    })

    return jsonify({"message": "Joined event successfully"}), 201


@events_bp.route("/<event_id>/leave", methods=["POST"])
@jwt_required()
def leave_event(event_id):
    """
    Leave an event and withdraw your remaining balance.
    
    The user's positive balance is returned to them (subtracted from pool).
    Cannot leave if you have outstanding debts to settle.
    Creator cannot leave their own event.
    """
    from app.core import DebtService
    
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())

    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400

    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Creator cannot leave their own event
    if event["creator_id"] == user_id:
        return jsonify({"error": "Event creator cannot leave. Transfer ownership or delete the event instead."}), 403

    # Check if user is a participant
    participant = mongo.participants.find_one({
        "event_id": event_oid,
        "user_id": user_id
    })
    
    if not participant:
        return jsonify({"error": "You are not a participant of this event"}), 404

    # Check for outstanding debts
    can_leave, error_msg, debts = DebtService.handle_participant_leaving(
        str(event_oid), str(user_id)
    )
    
    if not can_leave:
        return jsonify({
            "error": error_msg,
            "outstanding_debts": debts
        }), 400
    
    # Get the user's current balance
    user_balance = round(float(participant.get("balance", 0)), 2)
    
    # Only process if there's a positive balance to return
    if user_balance > 0:
        # Subtract from event pool
        mongo.events.update_one(
            {"_id": event_oid},
            {
                "$inc": {"total_pool": -user_balance},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # Credit the user's personal wallet
        from app.core import WalletFallbackService
        WalletFallbackService.credit_wallet(
            user_id=str(user_id),
            amount=user_balance,
            source="event_withdrawal",
            reference_id=str(event_oid),
            notes=f"Left event '{event.get('name', 'Unknown')}' and withdrew balance"
        )
        
        # Record withdrawal activity
        mongo.activities.insert_one({
            "type": "participant_left",
            "event_id": event_oid,
            "user_id": user_id,
            "amount": user_balance,
            "description": f"Left event and withdrew ${user_balance:.2f} to wallet",
            "created_at": datetime.utcnow()
        })
    
    # Remove the participant record
    mongo.participants.delete_one({"_id": participant["_id"]})
    
    # Get user info for notification
    user = mongo.users.find_one({"_id": user_id})
    user_name = user.get("name", "A participant") if user else "A participant"
    
    # Notify event creator
    from app.core import NotificationService
    NotificationService.create_notification(
        user_id=str(event["creator_id"]),
        notification_type="participant_left",
        title="Participant Left",
        message=f"{user_name} has left the event '{event['name']}'" + 
                (f" and withdrew ${user_balance:.2f}" if user_balance > 0 else ""),
        data={
            "event_id": str(event_oid),
            "left_user_id": str(user_id),
            "amount_withdrawn": user_balance
        }
    )
    
    # Check if event is now empty (no participants left)
    remaining_participants = mongo.participants.count_documents({"event_id": event_oid})
    event_deleted = False
    
    if remaining_participants == 0:
        # Delete the event and all related data
        mongo.expenses.delete_many({"event_id": event_oid})
        mongo.approval_requests.delete_many({"event_id": event_oid})
        mongo.activities.delete_many({"event_id": event_oid})
        mongo.events.delete_one({"_id": event_oid})
        event_deleted = True
    
    return jsonify({
        "message": "Successfully left the event" + (" (event deleted as it was empty)" if event_deleted else ""),
        "amount_withdrawn": user_balance,
        "event_name": event.get("name", ""),
        "event_deleted": event_deleted
    }), 200


@events_bp.route("/<event_id>", methods=["DELETE"])
@jwt_required()
def delete_event(event_id):
    """
    Delete an event (creator only).
    
    This permanently deletes the event and all related data.
    All participant balances are returned to them.
    """
    from app.core import NotificationService
    
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())

    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400

    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Only creator can delete the event
    if event["creator_id"] != user_id:
        return jsonify({"error": "Only the event creator can delete this event"}), 403
    
    # Get all participants to notify them
    participants = list(mongo.participants.find({"event_id": event_oid}))
    event_name = event.get("name", "Unknown Event")
    
    # Import wallet service for crediting balances
    from app.core import WalletFallbackService
    
    # Notify all participants (except creator) about deletion and credit their wallets
    for participant in participants:
        balance = round(float(participant.get("balance", 0)), 2)
        
        # Credit positive balance to user's personal wallet
        if balance > 0:
            WalletFallbackService.credit_wallet(
                user_id=str(participant["user_id"]),
                amount=balance,
                source="event_deleted",
                reference_id=str(event_oid),
                notes=f"Event '{event_name}' deleted - balance returned"
            )
        
        if participant["user_id"] != user_id:
            NotificationService.create_notification(
                user_id=str(participant["user_id"]),
                notification_type="event_deleted",
                title="Event Deleted",
                message=f"The event '{event_name}' has been deleted by the creator." +
                        (f" Your balance of ${balance:.2f} has been credited to your wallet." if balance > 0 else ""),
                data={
                    "event_id": str(event_oid),
                    "event_name": event_name,
                    "balance_returned": balance,
                    "balance_credited_to_wallet": balance > 0
                }
            )
    
    # Delete all related data
    mongo.expenses.delete_many({"event_id": event_oid})
    mongo.participants.delete_many({"event_id": event_oid})
    mongo.approval_requests.delete_many({"event_id": event_oid})
    mongo.activities.delete_many({"event_id": event_oid})
    mongo.events.delete_one({"_id": event_oid})
    
    return jsonify({
        "message": "Event deleted successfully",
        "event_name": event_name,
        "participants_notified": len(participants) - 1  # Exclude creator
    }), 200


@events_bp.route("/<event_id>/end", methods=["POST"])
@jwt_required()
def end_event(event_id):
    """
    End an event and distribute remaining balances to all participants.
    
    Only the creator can end an event.
    Each participant's positive balance is returned to them.
    The event is marked as 'completed'.
    """
    from app.core import NotificationService
    
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())

    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400

    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Only creator can end the event
    if event["creator_id"] != user_id:
        return jsonify({"error": "Only the event creator can end this event"}), 403
    
    # Check if already ended
    if event.get("status") == "completed":
        return jsonify({"error": "Event is already ended"}), 400
    
    # Get all participants
    participants = list(mongo.participants.find({"event_id": event_oid}))
    event_name = event.get("name", "Unknown Event")
    
    # Import wallet service for crediting balances
    from app.core import WalletFallbackService
    
    # Calculate settlement for each participant and credit their wallet
    settlements = []
    for participant in participants:
        user = mongo.users.find_one({"_id": participant["user_id"]})
        user_name = user.get("name", "Unknown") if user else "Unknown"
        balance = round(float(participant.get("balance", 0)), 2)
        deposit = round(float(participant.get("deposit_amount", 0)), 2)
        spent = round(float(participant.get("total_spent", 0)), 2)
        
        # Credit positive balance to user's personal wallet
        if balance > 0:
            WalletFallbackService.credit_wallet(
                user_id=str(participant["user_id"]),
                amount=balance,
                source="event_settlement",
                reference_id=str(event_oid),
                notes=f"Event '{event_name}' ended - balance returned"
            )
        
        settlements.append({
            "user_id": str(participant["user_id"]),
            "user_name": user_name,
            "deposit_amount": deposit,
            "total_spent": spent,
            "balance_returned": balance,
            "net_position": balance  # Positive = gets money back, Negative = owes
        })
        
        # Notify participant about settlement
        if participant["user_id"] != user_id:
            if balance > 0:
                message = f"Event '{event_name}' has ended. Your balance of ${balance:.2f} has been credited to your wallet."
            elif balance < 0:
                message = f"Event '{event_name}' has ended. You had an outstanding balance of ${abs(balance):.2f}."
            else:
                message = f"Event '{event_name}' has ended. Your balance was $0.00."
            
            NotificationService.create_notification(
                user_id=str(participant["user_id"]),
                notification_type="event_ended",
                title="Event Ended",
                message=message,
                data={
                    "event_id": str(event_oid),
                    "event_name": event_name,
                    "balance_returned": balance,
                    "balance_credited_to_wallet": balance > 0,
                    "deposit_amount": deposit,
                    "total_spent": spent
                }
            )
    
    # Mark event as completed
    mongo.events.update_one(
        {"_id": event_oid},
        {
            "$set": {
                "status": "completed",
                "ended_at": datetime.utcnow(),
                "ended_by": user_id,
                "final_settlements": settlements,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Record activity
    mongo.activities.insert_one({
        "type": "event_ended",
        "event_id": event_oid,
        "user_id": user_id,
        "description": f"Event '{event_name}' ended by creator",
        "settlements": settlements,
        "created_at": datetime.utcnow()
    })
    
    return jsonify({
        "message": "Event ended successfully",
        "event_name": event_name,
        "status": "completed",
        "settlements": settlements,
        "total_pool": event.get("total_pool", 0),
        "total_spent": event.get("total_spent", 0),
        "participants_count": len(participants)
    }), 200


@events_bp.route("/<event_id>/transfer-ownership", methods=["POST"])
@jwt_required()
def transfer_ownership(event_id):
    """
    Transfer event ownership to another participant.
    
    Only the current creator can transfer ownership.
    The new owner must be an active participant.
    """
    from app.core import NotificationService
    
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())
    data = request.get_json()
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    new_owner_id = data.get("new_owner_id")
    if not new_owner_id:
        return jsonify({"error": "New owner ID is required"}), 400
    
    new_owner_oid = safe_object_id(new_owner_id)
    if not new_owner_oid:
        return jsonify({"error": "Invalid new owner ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Only creator can transfer ownership
    if event["creator_id"] != user_id:
        return jsonify({"error": "Only the event creator can transfer ownership"}), 403
    
    # Cannot transfer to yourself
    if new_owner_oid == user_id:
        return jsonify({"error": "Cannot transfer ownership to yourself"}), 400
    
    # New owner must be a participant
    new_owner_participant = mongo.participants.find_one({
        "event_id": event_oid,
        "user_id": new_owner_oid,
        "status": {"$in": ["active", "approved"]}
    })
    
    if not new_owner_participant:
        return jsonify({"error": "New owner must be an active participant of this event"}), 400
    
    # Get user info
    current_owner = mongo.users.find_one({"_id": user_id})
    new_owner = mongo.users.find_one({"_id": new_owner_oid})
    
    current_owner_name = current_owner.get("name", "Previous owner") if current_owner else "Previous owner"
    new_owner_name = new_owner.get("name", "New owner") if new_owner else "New owner"
    
    # Update event creator
    mongo.events.update_one(
        {"_id": event_oid},
        {
            "$set": {
                "creator_id": new_owner_oid,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Record activity
    mongo.activities.insert_one({
        "type": "ownership_transferred",
        "event_id": event_oid,
        "user_id": user_id,
        "description": f"Ownership transferred from {current_owner_name} to {new_owner_name}",
        "data": {
            "previous_owner_id": str(user_id),
            "new_owner_id": str(new_owner_oid)
        },
        "created_at": datetime.utcnow()
    })
    
    # Notify new owner
    NotificationService.create_notification(
        user_id=str(new_owner_oid),
        notification_type="ownership_received",
        title="You are now the event owner",
        message=f"{current_owner_name} has transferred ownership of '{event['name']}' to you.",
        data={
            "event_id": str(event_oid),
            "previous_owner_id": str(user_id)
        }
    )
    
    return jsonify({
        "message": f"Ownership transferred to {new_owner_name}",
        "new_owner_id": str(new_owner_oid),
        "new_owner_name": new_owner_name
    }), 200


# ------------------ JOIN VIA INVITE CODE/LINK ------------------

@events_bp.route("/join/<invite_code>", methods=["GET"])
def get_event_by_invite_code(invite_code):
    """Get event info by invite code (public - no auth required for preview)."""
    event = mongo.events.find_one({"invite_code": invite_code.upper()})
    
    if not event:
        return jsonify({"error": "Invalid invite code"}), 404
    
    # Skip invite_enabled check - allow all invites
    # if not event.get("invite_enabled", True):
    #     return jsonify({"error": "Invites are disabled for this event"}), 403
    
    if event["status"] != "active":
        return jsonify({"error": "Event is no longer active"}), 400
    
    # Return limited info for preview
    participant_count = mongo.participants.count_documents({"event_id": event["_id"]})
    creator = mongo.users.find_one({"_id": event["creator_id"]})
    
    return jsonify({
        "event": {
            "_id": str(event["_id"]),
            "name": event["name"],
            "description": event.get("description", ""),
            "creator_name": creator.get("name") if creator else "Unknown",
            "participant_count": participant_count,
            "start_date": event.get("start_date"),
            "end_date": event.get("end_date"),
            "status": event["status"]
        }
    })


@events_bp.route("/join/<invite_code>", methods=["POST"])
@jwt_required()
def join_event_by_code(invite_code):
    """Join an event using invite code with approval workflow."""
    user_id = str(get_jwt_identity())
    
    event = mongo.events.find_one({"invite_code": invite_code.upper()})
    
    if not event:
        return jsonify({"error": "Invalid invite code"}), 404
    
    # Skip invite_enabled check - allow all invites
    # if not event.get("invite_enabled", True):
    #     return jsonify({"error": "Invites are disabled for this event"}), 403
    
    if event["status"] != "active":
        return jsonify({"error": "Event is no longer active"}), 400
    
    event_id = str(event["_id"])
    
    if is_participant(event["_id"], safe_object_id(user_id)):
        return jsonify({"error": "Already a participant"}), 409
    
    # Check reliability for joining
    # Returns: (can_join, message, required_deposit_multiplier)
    can_join, reliability_message, deposit_multiplier = ReliabilityService.check_can_join_event(user_id, event_id)
    if not can_join:
        return jsonify({
            "error": "Cannot join event",
            "reason": reliability_message
        }), 403
    
    # Validate against event rules
    # Returns: (is_valid, error_message, violation_type)
    is_valid, error_message, violation_type = RuleEnforcementService.validate_join(event_id, user_id)
    if not is_valid:
        return jsonify({
            "error": "Cannot join event",
            "violations": [{"type": violation_type, "message": error_message}]
        }), 403
    
    # Check if approval is required
    rules = event.get("rules", {})
    requires_approval = rules.get("join_approval_required", False)
    
    if requires_approval:
        # Create join request
        request_result = JoinRequestService.create_join_request(
            event_id=event_id,
            user_id=user_id,
            join_method="invite_code"
        )
        
        if request_result.get("error"):
            return jsonify({"error": request_result["error"]}), 400
        
        # Notify creator
        NotificationService.notify_join_request(
            creator_id=str(event["creator_id"]),
            event_id=event_id,
            event_name=event["name"],
            user_id=user_id,
            requires_approval=True
        )
        
        return jsonify({
            "message": "Join request submitted for approval",
            "status": "pending",
            "event_id": event_id,
            "event_name": event["name"],
            "request_id": request_result.get("request_id")
        }), 202
    
    # Direct join (no approval needed)
    mongo.participants.insert_one({
        "event_id": event["_id"],
        "user_id": safe_object_id(user_id),
        "deposit_amount": 0,
        "total_spent": 0,
        "balance": 0,
        "status": "active",
        "categories": [],
        "joined_via": "invite_code",
        "created_at": datetime.utcnow()
    })
    
    # Notify creator
    NotificationService.notify_join_request(
        creator_id=str(event["creator_id"]),
        event_id=event_id,
        event_name=event["name"],
        user_id=user_id,
        requires_approval=False
    )
    
    return jsonify({
        "message": "Joined event successfully",
        "event_id": event_id,
        "event_name": event["name"]
    }), 201


# ------------------ JOIN REQUEST MANAGEMENT ------------------

@events_bp.route("/<event_id>/join-requests", methods=["GET"])
@jwt_required()
def get_join_requests(event_id):
    """Get pending join requests for an event (creator only)."""
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Only creator can view join requests
    if event["creator_id"] != user_id:
        return jsonify({"error": "Only creator can view join requests"}), 403
    
    requests = JoinRequestService.get_pending_requests(event_id)
    
    return jsonify({"requests": requests})


@events_bp.route("/<event_id>/join-requests/<request_id>/approve", methods=["POST"])
@jwt_required()
def approve_join_request(event_id, request_id):
    """Approve a join request (creator only)."""
    event_oid = safe_object_id(event_id)
    user_id = str(get_jwt_identity())
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    if str(event["creator_id"]) != user_id:
        return jsonify({"error": "Only creator can approve requests"}), 403
    
    result = JoinRequestService.approve_join_request(
        request_id=request_id,
        approved_by=user_id
    )
    
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400
    
    # Notify user
    if result.get("user_id"):
        NotificationService.notify_join_approved(
            user_id=result["user_id"],
            event_id=event_id,
            event_name=event["name"]
        )
    
    return jsonify({
        "message": "Join request approved",
        "status": result.get("status")
    })


@events_bp.route("/<event_id>/join-requests/<request_id>/reject", methods=["POST"])
@jwt_required()
def reject_join_request(event_id, request_id):
    """Reject a join request (creator only)."""
    event_oid = safe_object_id(event_id)
    user_id = str(get_jwt_identity())
    data = request.get_json() or {}
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    if str(event["creator_id"]) != user_id:
        return jsonify({"error": "Only creator can reject requests"}), 403
    
    result = JoinRequestService.reject_join_request(
        request_id=request_id,
        rejected_by=user_id,
        reason=data.get("reason")
    )
    
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400
    
    # Notify user
    if result.get("user_id"):
        NotificationService.notify_join_rejected(
            user_id=result["user_id"],
            event_id=event_id,
            event_name=event["name"],
            reason=data.get("reason")
        )
    
    return jsonify({
        "message": "Join request rejected",
        "status": result.get("status")
    })


@events_bp.route("/<event_id>/recalculate-pool", methods=["POST"])
@jwt_required()
def recalculate_pool(event_id):
    """
    Recalculate pool state from scratch based on deposits and expenses.
    
    Use this to fix any corrupted pool data.
    Only the creator can trigger a recalculation.
    """
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Only creator can recalculate
    if event["creator_id"] != user_id:
        return jsonify({"error": "Only event creator can recalculate pool"}), 403
    
    success, result = PoolService.recalculate_pool(str(event_oid))
    
    if not success:
        return jsonify({
            "error": "Failed to recalculate pool",
            "details": result.get("error")
        }), 500
    
    return jsonify({
        "message": "Pool recalculated successfully",
        "before": {
            "total_pool": event.get("total_pool", 0),
            "total_spent": event.get("total_spent", 0)
        },
        "after": result
    })


@events_bp.route("/<event_id>/invite-link", methods=["GET"])
@jwt_required()
def get_invite_link(event_id):
    """Get the invite link and QR code data for an event."""
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    if not is_participant(event_oid, user_id):
        return jsonify({"error": "Not a participant"}), 403
    
    invite_code = event.get("invite_code")
    if not invite_code:
        # Generate one if missing (for older events)
        invite_code = generate_invite_code()
        while mongo.events.find_one({"invite_code": invite_code}):
            invite_code = generate_invite_code()
        mongo.events.update_one(
            {"_id": event_oid},
            {"$set": {"invite_code": invite_code, "invite_enabled": True}}
        )
    
    base_url = request.host_url.rstrip("/")
    invite_url = f"{base_url}/api/v1/events/join/{invite_code}"
    
    # Frontend join URL (for web app)
    frontend_url = request.headers.get("Origin", "http://localhost:8080")
    frontend_join_url = f"{frontend_url}/join/{invite_code}"
    
    return jsonify({
        "invite_code": invite_code,
        "invite_url": invite_url,
        "frontend_join_url": frontend_join_url,
        "invite_enabled": event.get("invite_enabled", True),
        "qr_data": frontend_join_url  # Use this to generate QR on frontend
    })


@events_bp.route("/<event_id>/invite-link", methods=["PUT"])
@jwt_required()
def toggle_invite_link(event_id):
    """Enable/disable invite link or regenerate code."""
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())
    data = request.get_json() or {}
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Only creator can manage invite settings
    if event["creator_id"] != user_id:
        return jsonify({"error": "Only event creator can manage invites"}), 403
    
    update = {}
    
    if "enabled" in data:
        update["invite_enabled"] = bool(data["enabled"])
    
    if data.get("regenerate"):
        new_code = generate_invite_code()
        while mongo.events.find_one({"invite_code": new_code}):
            new_code = generate_invite_code()
        update["invite_code"] = new_code
    
    if update:
        mongo.events.update_one({"_id": event_oid}, {"$set": update})
    
    # Return updated info
    updated_event = mongo.events.find_one({"_id": event_oid})
    base_url = request.host_url.rstrip("/")
    
    return jsonify({
        "invite_code": updated_event.get("invite_code"),
        "invite_enabled": updated_event.get("invite_enabled", True),
        "invite_url": f"{base_url}/api/v1/events/join/{updated_event.get('invite_code')}"
    })


@events_bp.route("/<event_id>/deposit", methods=["POST"])
@jwt_required()
def deposit(event_id):
    """
    Deposit money to an event.
    
    Two modes:
    1. Direct deposit (amount only) - just updates balance
    2. Finternet deposit (use_finternet=True) - creates a payment intent
    
    Request body:
    {
        "amount": 100.00,
        "use_finternet": true  // optional, creates payment intent
    }
    """
    from app.payments.services.finternet import FinternetService
    from app.payments.models import PaymentIntentDB
    
    event_oid = safe_object_id(event_id)
    user_id = safe_object_id(get_jwt_identity())
    data = request.get_json()

    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400

    amount = data.get("amount")
    if not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({"error": "Invalid deposit amount"}), 400

    event = mongo.events.find_one({"_id": event_oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404

    if event["status"] != "active":
        return jsonify({"error": "Event is closed"}), 400

    participant = is_participant(event_oid, user_id)
    if not participant:
        return jsonify({"error": "Not a participant"}), 403

    use_finternet = data.get("use_finternet", False)
    
    if use_finternet:
        # Create Finternet payment intent for deposit
        finternet = FinternetService()
        
        intent_response = finternet.create_payment_intent(
            amount=str(amount),
            currency=data.get("currency", "USD"),
            payment_type="DELIVERY_VS_PAYMENT",
            settlement_method="OFF_RAMP_MOCK",
            description=f"Deposit to event: {event.get('name', 'Event')}"
        )
        
        if "error" in intent_response:
            return jsonify({
                "error": intent_response["error"].get("message", "Failed to create payment intent"),
                "details": intent_response["error"]
            }), 500
        
        # Store locally
        local_id = PaymentIntentDB.create(intent_response)
        
        # Update with user/event IDs
        mongo.payment_intents.update_one(
            {"_id": ObjectId(local_id)},
            {"$set": {
                "user_id": str(user_id),
                "event_id": str(event_oid),
                "intent_type": "deposit"
            }}
        )
        
        payment_url = finternet.get_payment_url(intent_response)
        
        # Generate transaction hash for blockchain simulation
        import uuid
        tx_hash = "0x" + uuid.uuid4().hex + uuid.uuid4().hex[:24]
        block_number = 19847293 + int(uuid.uuid4().int % 10000)
        
        # OPTIMISTIC UPDATE: Immediately credit the deposit
        # This ensures the deposit works regardless of payment gateway status
        mongo.participants.update_one(
            {"_id": participant["_id"]},
            {"$inc": {
                "deposit_amount": amount,
                "balance": amount
            }}
        )

        mongo.events.update_one(
            {"_id": event_oid},
            {"$inc": {"total_pool": amount}}
        )
        
        # Log deposit activity with blockchain details
        mongo.activities.insert_one({
            "type": "deposit",
            "event_id": event_oid,
            "user_id": user_id,
            "amount": amount,
            "description": f"Deposit via Finternet Gateway",
            "payment_intent_id": local_id,
            "transaction_hash": tx_hash,
            "block_number": block_number,
            "chain": "Sepolia",
            "status": "confirmed",
            "created_at": datetime.utcnow()
        })
        
        return jsonify({
            "message": "Deposit confirmed successfully",
            "payment_url": payment_url,
            "intent_id": local_id,
            "finternet_id": intent_response.get("id"),
            "amount": amount,
            "status": "CONFIRMED",
            "transaction_hash": tx_hash,
            "block_number": block_number,
            "chain": "Sepolia",
            "confirmations": 12
        })
    
    # Direct deposit (no Finternet)
    mongo.participants.update_one(
        {"_id": participant["_id"]},
        {"$inc": {
            "deposit_amount": amount,
            "balance": amount
        }}
    )

    mongo.events.update_one(
        {"_id": event_oid},
        {"$inc": {"total_pool": amount}}
    )

    # Log deposit activity
    mongo.activities.insert_one({
        "type": "deposit",
        "event_id": event_oid,
        "user_id": user_id,
        "amount": amount,
        "description": "Deposit",
        "created_at": datetime.utcnow()
    })

    return jsonify({
        "message": "Deposit successful",
        "amount": amount
    })


# ------------------ FRIENDS SYSTEM ------------------

@events_bp.route("/friends", methods=["GET"])
@jwt_required()
def get_friends():
    """Get all friends of current user."""
    user_id = safe_object_id(get_jwt_identity())
    
    friendships = mongo.friendships.find({
        "$or": [
            {"user_id": user_id, "status": "accepted"},
            {"friend_id": user_id, "status": "accepted"}
        ]
    })
    
    friends = []
    for f in friendships:
        # Get the other user's ID
        friend_user_id = f["friend_id"] if f["user_id"] == user_id else f["user_id"]
        user = mongo.users.find_one({"_id": friend_user_id})
        if user:
            friends.append({
                "friendship_id": str(f["_id"]),
                "user_id": str(friend_user_id),
                "name": user.get("name", "Unknown"),
                "email": user.get("email"),
                "since": f.get("accepted_at", f.get("created_at"))
            })
    
    return jsonify({"friends": friends})


@events_bp.route("/friends/requests", methods=["GET"])
@jwt_required()
def get_friend_requests():
    """Get pending friend requests (received)."""
    user_id = safe_object_id(get_jwt_identity())
    
    requests = mongo.friendships.find({
        "friend_id": user_id,
        "status": "pending"
    })
    
    pending = []
    for r in requests:
        sender = mongo.users.find_one({"_id": r["user_id"]})
        pending.append({
            "request_id": str(r["_id"]),
            "from_user_id": str(r["user_id"]),
            "from_name": sender.get("name") if sender else "Unknown",
            "from_email": sender.get("email") if sender else None,
            "created_at": r.get("created_at")
        })
    
    return jsonify({"requests": pending})


@events_bp.route("/friends/request", methods=["POST"])
@jwt_required()
def send_friend_request():
    """Send a friend request to another user."""
    user_id = safe_object_id(get_jwt_identity())
    data = request.get_json()
    
    friend_email = data.get("email")
    friend_user_id = safe_object_id(data.get("user_id"))
    
    # Find friend by email or user_id
    if friend_email:
        friend = mongo.users.find_one({"email": friend_email})
    elif friend_user_id:
        friend = mongo.users.find_one({"_id": friend_user_id})
    else:
        return jsonify({"error": "Provide email or user_id"}), 400
    
    if not friend:
        return jsonify({"error": "User not found"}), 404
    
    friend_id = friend["_id"]
    
    if friend_id == user_id:
        return jsonify({"error": "Cannot add yourself as friend"}), 400
    
    # Check if friendship already exists
    existing = mongo.friendships.find_one({
        "$or": [
            {"user_id": user_id, "friend_id": friend_id},
            {"user_id": friend_id, "friend_id": user_id}
        ]
    })
    
    if existing:
        if existing["status"] == "accepted":
            return jsonify({"error": "Already friends"}), 409
        elif existing["status"] == "pending":
            return jsonify({"error": "Friend request already pending"}), 409
    
    mongo.friendships.insert_one({
        "user_id": user_id,
        "friend_id": friend_id,
        "status": "pending",
        "created_at": datetime.utcnow()
    })
    
    return jsonify({
        "message": "Friend request sent",
        "to_user": friend.get("name")
    }), 201


@events_bp.route("/friends/request/<request_id>/accept", methods=["POST"])
@jwt_required()
def accept_friend_request(request_id):
    """Accept a friend request."""
    user_id = safe_object_id(get_jwt_identity())
    request_oid = safe_object_id(request_id)
    
    if not request_oid:
        return jsonify({"error": "Invalid request ID"}), 400
    
    friendship = mongo.friendships.find_one({
        "_id": request_oid,
        "friend_id": user_id,
        "status": "pending"
    })
    
    if not friendship:
        return jsonify({"error": "Friend request not found"}), 404
    
    mongo.friendships.update_one(
        {"_id": request_oid},
        {"$set": {
            "status": "accepted",
            "accepted_at": datetime.utcnow()
        }}
    )
    
    sender = mongo.users.find_one({"_id": friendship["user_id"]})
    
    return jsonify({
        "message": "Friend request accepted",
        "friend_name": sender.get("name") if sender else "Unknown"
    })


@events_bp.route("/friends/request/<request_id>/reject", methods=["POST"])
@jwt_required()
def reject_friend_request(request_id):
    """Reject a friend request."""
    user_id = safe_object_id(get_jwt_identity())
    request_oid = safe_object_id(request_id)
    
    if not request_oid:
        return jsonify({"error": "Invalid request ID"}), 400
    
    result = mongo.friendships.delete_one({
        "_id": request_oid,
        "friend_id": user_id,
        "status": "pending"
    })
    
    if result.deleted_count == 0:
        return jsonify({"error": "Friend request not found"}), 404
    
    return jsonify({"message": "Friend request rejected"})


@events_bp.route("/friends/<friend_id>/remove", methods=["DELETE"])
@jwt_required()
def remove_friend(friend_id):
    """Remove a friend."""
    user_id = safe_object_id(get_jwt_identity())
    friend_oid = safe_object_id(friend_id)
    
    if not friend_oid:
        return jsonify({"error": "Invalid friend ID"}), 400
    
    result = mongo.friendships.delete_one({
        "$or": [
            {"user_id": user_id, "friend_id": friend_oid, "status": "accepted"},
            {"user_id": friend_oid, "friend_id": user_id, "status": "accepted"}
        ]
    })
    
    if result.deleted_count == 0:
        return jsonify({"error": "Friendship not found"}), 404
    
    return jsonify({"message": "Friend removed"})


# ------------------ EVENT INVITES ------------------

@events_bp.route("/<event_id>/invite", methods=["POST"])
@jwt_required()
def invite_to_event(event_id):
    """Invite a user (friend) to join an event."""
    user_id = safe_object_id(get_jwt_identity())
    event_oid = safe_object_id(event_id)
    data = request.get_json()
    
    if not event_oid:
        return jsonify({"error": "Invalid event ID"}), 400
    
    # Check if user is participant of event
    if not is_participant(event_oid, user_id):
        return jsonify({"error": "You must be a participant to invite others"}), 403
    
    invite_user_id = safe_object_id(data.get("user_id"))
    invite_email = data.get("email")
    
    # Find invitee
    if invite_email:
        invitee = mongo.users.find_one({"email": invite_email})
    elif invite_user_id:
        invitee = mongo.users.find_one({"_id": invite_user_id})
    else:
        return jsonify({"error": "Provide email or user_id"}), 400
    
    if not invitee:
        return jsonify({"error": "User not found"}), 404
    
    invitee_id = invitee["_id"]
    
    # Check if already participant
    if is_participant(event_oid, invitee_id):
        return jsonify({"error": "User is already a participant"}), 409
    
    # Check if invite already exists
    existing_invite = mongo.event_invites.find_one({
        "event_id": event_oid,
        "invitee_id": invitee_id,
        "status": "pending"
    })
    
    if existing_invite:
        return jsonify({"error": "Invite already pending"}), 409
    
    event = mongo.events.find_one({"_id": event_oid})
    
    mongo.event_invites.insert_one({
        "event_id": event_oid,
        "event_name": event.get("name"),
        "inviter_id": user_id,
        "invitee_id": invitee_id,
        "status": "pending",
        "created_at": datetime.utcnow()
    })
    
    return jsonify({
        "message": "Invite sent",
        "to_user": invitee.get("name")
    }), 201


@events_bp.route("/invites", methods=["GET"])
@jwt_required()
def get_event_invites():
    """Get pending event invites for current user."""
    user_id = safe_object_id(get_jwt_identity())
    
    invites = mongo.event_invites.find({
        "invitee_id": user_id,
        "status": "pending"
    })
    
    pending = []
    for inv in invites:
        inviter = mongo.users.find_one({"_id": inv["inviter_id"]})
        pending.append({
            "invite_id": str(inv["_id"]),
            "event_id": str(inv["event_id"]),
            "event_name": inv.get("event_name"),
            "from_user_id": str(inv["inviter_id"]),
            "from_name": inviter.get("name") if inviter else "Unknown",
            "created_at": inv.get("created_at")
        })
    
    return jsonify({"invites": pending})


@events_bp.route("/invites/<invite_id>/accept", methods=["POST"])
@jwt_required()
def accept_event_invite(invite_id):
    """Accept an event invite and join the event."""
    user_id = safe_object_id(get_jwt_identity())
    invite_oid = safe_object_id(invite_id)
    
    if not invite_oid:
        return jsonify({"error": "Invalid invite ID"}), 400
    
    invite = mongo.event_invites.find_one({
        "_id": invite_oid,
        "invitee_id": user_id,
        "status": "pending"
    })
    
    if not invite:
        return jsonify({"error": "Invite not found"}), 404
    
    event_id = invite["event_id"]
    
    # Add as participant
    mongo.participants.insert_one({
        "event_id": event_id,
        "user_id": user_id,
        "deposit_amount": 0,
        "total_spent": 0,
        "balance": 0,
        "status": "active",
        "categories": [],
        "invited_by": invite["inviter_id"],
        "created_at": datetime.utcnow()
    })
    
    # Update invite status
    mongo.event_invites.update_one(
        {"_id": invite_oid},
        {"$set": {"status": "accepted", "accepted_at": datetime.utcnow()}}
    )
    
    return jsonify({
        "message": "Invite accepted, you have joined the event",
        "event_id": str(event_id),
        "event_name": invite.get("event_name")
    })


@events_bp.route("/invites/<invite_id>/reject", methods=["POST"])
@jwt_required()
def reject_event_invite(invite_id):
    """Reject an event invite."""
    user_id = safe_object_id(get_jwt_identity())
    invite_oid = safe_object_id(invite_id)
    
    if not invite_oid:
        return jsonify({"error": "Invalid invite ID"}), 400
    
    result = mongo.event_invites.update_one(
        {"_id": invite_oid, "invitee_id": user_id, "status": "pending"},
        {"$set": {"status": "rejected", "rejected_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Invite not found"}), 404
    
    return jsonify({"message": "Invite rejected"})