from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from app.extensions import db as mongo

events_bp = Blueprint("events", __name__)

@events_bp.route("/", methods=["POST"])
@jwt_required()
def create_event():
    uid = get_jwt_identity()
    data = request.get_json()

    event = {
        "name": data["name"],
        "description": data.get("description", ""),
        "creator_id": ObjectId(uid),
        "status": "active",
        "merkle_root": None,
        "created_at": datetime.utcnow()
    }

    res = mongo.db.events.insert_one(event)

    mongo.db.participants.insert_one({
        "event_id": res.inserted_id,
        "user_id": ObjectId(uid),
        "deposit_amount": 0,
        "balance": 0,
        "total_spent": 0,
        "status": "active"
    })

    event["_id"] = str(res.inserted_id)
    return jsonify({"event": event}), 201


@events_bp.route("/", methods=["GET"])
@jwt_required()
def list_events():
    uid = get_jwt_identity()
    parts = mongo.db.participants.find({"user_id": ObjectId(uid)})

    ids = [p["event_id"] for p in parts]
    events = list(mongo.db.events.find({"_id": {"$in": ids}}))

    for e in events:
        e["_id"] = str(e["_id"])
        e["creator_id"] = str(e["creator_id"])

    return jsonify({"events": events})