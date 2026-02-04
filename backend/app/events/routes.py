from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId, errors
from datetime import datetime
import secrets
import hashlib
from app.extensions import db as mongo

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
        "rules": data.get("rules", {
            "spending_limit": None,
            "approval_required": False,
            "auto_approve_under": 100
        }),
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


# ------------------ JOIN VIA INVITE CODE/LINK ------------------

@events_bp.route("/join/<invite_code>", methods=["GET"])
def get_event_by_invite_code(invite_code):
    """Get event info by invite code (public - no auth required for preview)."""
    event = mongo.events.find_one({"invite_code": invite_code.upper()})
    
    if not event:
        return jsonify({"error": "Invalid invite code"}), 404
    
    if not event.get("invite_enabled", True):
        return jsonify({"error": "Invites are disabled for this event"}), 403
    
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
    """Join an event using invite code."""
    user_id = safe_object_id(get_jwt_identity())
    
    event = mongo.events.find_one({"invite_code": invite_code.upper()})
    
    if not event:
        return jsonify({"error": "Invalid invite code"}), 404
    
    if not event.get("invite_enabled", True):
        return jsonify({"error": "Invites are disabled for this event"}), 403
    
    if event["status"] != "active":
        return jsonify({"error": "Event is no longer active"}), 400
    
    event_oid = event["_id"]
    
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
        "joined_via": "invite_code",
        "created_at": datetime.utcnow()
    })
    
    return jsonify({
        "message": "Joined event successfully",
        "event_id": str(event_oid),
        "event_name": event["name"]
    }), 201


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
            currency=data.get("currency", "USDC"),
            payment_type="CONDITIONAL",
            settlement_method="OFF_RAMP_MOCK",
            description=f"Deposit to event: {event.get('name', 'Event')}",
            metadata={
                "user_id": str(user_id),
                "event_id": str(event_oid),
                "type": "deposit"
            }
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
        
        # Log pending deposit activity
        mongo.activities.insert_one({
            "type": "deposit_pending",
            "event_id": event_oid,
            "user_id": user_id,
            "amount": amount,
            "description": "Deposit (pending payment)",
            "payment_intent_id": local_id,
            "created_at": datetime.utcnow()
        })
        
        return jsonify({
            "message": "Payment intent created",
            "payment_url": payment_url,
            "intent_id": local_id,
            "finternet_id": intent_response.get("id"),
            "amount": amount
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