from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from app.extensions import mongo

events_bp = Blueprint('events', __name__)

@events_bp.route('/', methods=['POST'])
@jwt_required()
def create_event():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    event = {
        "name": data['name'],
        "description": data.get('description', ''),
        "creator_id": ObjectId(user_id),
        "start_date": data.get('start_date'),
        "end_date": data.get('end_date'),
        "status": "active",
        "shared_wallet_id": None,
        "merkle_root": None,
        "rules": {
            "spending_limit": None,
            "approval_required": False,
            "auto_approve_under": 100
        },
        "total_pool": 0,
        "total_spent": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = mongo.db.events.insert_one(event)
    event['_id'] = str(result.inserted_id)
    event['creator_id'] = str(event['creator_id'])
    
    # Add creator as participant
    participant = {
        "event_id": result.inserted_id,
        "user_id": ObjectId(user_id),
        "deposit_amount": 0,
        "total_spent": 0,
        "balance": 0,
        "status": "active",
        "categories": [],
        "created_at": datetime.utcnow()
    }
    mongo.db.participants.insert_one(participant)
    
    return jsonify({"event": event}), 201

@events_bp.route('/', methods=['GET'])
@jwt_required()
def get_user_events():
    user_id = get_jwt_identity()
    
    # Get events where user is participant
    participant_events = list(mongo.db.participants.find(
        {"user_id": ObjectId(user_id)}
    ))
    
    event_ids = [p['event_id'] for p in participant_events]
    events = list(mongo.db.events.find({"_id": {"$in": event_ids}}))
    
    for event in events:
        event['_id'] = str(event['_id'])
        event['creator_id'] = str(event['creator_id'])
    
    return jsonify({"events": events})

@events_bp.route('/<event_id>', methods=['GET'])
@jwt_required()
def get_event(event_id):
    event = mongo.db.events.find_one({"_id": ObjectId(event_id)})
    
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    event['_id'] = str(event['_id'])
    event['creator_id'] = str(event['creator_id'])
    
    # Get participants
    participants = list(mongo.db.participants.find({"event_id": ObjectId(event_id)}))
    for p in participants:
        p['_id'] = str(p['_id'])
        p['user_id'] = str(p['user_id'])
        p['event_id'] = str(p['event_id'])
        user = mongo.db.users.find_one({"_id": ObjectId(p['user_id'])})
        p['user_name'] = user['name'] if user else 'Unknown'
    
    event['participants'] = participants
    
    return jsonify({"event": event})

@events_bp.route('/<event_id>/join', methods=['POST'])
@jwt_required()
def join_event(event_id):
    user_id = get_jwt_identity()
    
    # Check if already participant
    existing = mongo.db.participants.find_one({
        "event_id": ObjectId(event_id),
        "user_id": ObjectId(user_id)
    })
    
    if existing:
        return jsonify({"error": "Already a participant"}), 409
    
    participant = {
        "event_id": ObjectId(event_id),
        "user_id": ObjectId(user_id),
        "deposit_amount": 0,
        "total_spent": 0,
        "balance": 0,
        "status": "active",
        "categories": [],
        "created_at": datetime.utcnow()
    }
    
    mongo.db.participants.insert_one(participant)
    
    return jsonify({"message": "Joined event successfully"})

@events_bp.route('/<event_id>/deposit', methods=['POST'])
@jwt_required()
def deposit(event_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    amount = data.get('amount', 0)
    
    # Update participant balance
    result = mongo.db.participants.update_one(
        {
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id)
        },
        {
            "$inc": {
                "deposit_amount": amount,
                "balance": amount
            }
        }
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Participant not found"}), 404
    
    # Update event total pool
    mongo.db.events.update_one(
        {"_id": ObjectId(event_id)},
        {"$inc": {"total_pool": amount}}
    )
    
    return jsonify({"message": "Deposit successful", "amount": amount})