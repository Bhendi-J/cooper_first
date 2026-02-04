from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from app.extensions import db as mongo

bp = Blueprint("dashboards", __name__, url_prefix="/dashboards")


@bp.route("/summary/<user_id>", methods=["GET"])
def summary(user_id):
    return jsonify({"user_id": user_id, "summary": {}})


@bp.route("/recent-activity", methods=["GET"])
@jwt_required()
def recent_activity():
    """
    Get recent activities (expenses and deposits) across all events the user participates in.
    Uses $lookup, $match, $sort, $limit for efficient querying.
    """
    uid = get_jwt_identity()
    user_oid = ObjectId(uid)
    limit = request.args.get("limit", 5, type=int)
    limit = min(limit, 50)  # Cap at 50
    
    # Get all event_ids where user is a participant
    participant_docs = list(mongo.participants.find({"user_id": user_oid}, {"event_id": 1}))
    event_ids = [p["event_id"] for p in participant_docs]
    
    if not event_ids:
        return jsonify({"activities": []})
    
    # Query activities collection for both deposits and expenses
    pipeline = [
        # Match activities for user's events
        {"$match": {"event_id": {"$in": event_ids}}},
        
        # Sort by created_at descending (most recent first)
        {"$sort": {"created_at": -1}},
        
        # Limit to requested number
        {"$limit": limit},
        
        # Lookup event name
        {"$lookup": {
            "from": "events",
            "localField": "event_id",
            "foreignField": "_id",
            "as": "event_info"
        }},
        
        # Lookup user name (who performed the action)
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user_info"
        }},
        
        # Project final fields
        {"$project": {
            "_id": {"$toString": "$_id"},
            "type": "$type",
            "description": "$description",
            "amount": "$amount",
            "event_id": {"$toString": "$event_id"},
            "event_name": {"$arrayElemAt": ["$event_info.name", 0]},
            "payer_id": {"$toString": "$user_id"},
            "payer_name": {"$arrayElemAt": ["$user_info.name", 0]},
            "created_at": "$created_at"
        }}
    ]
    
    activities = list(mongo.activities.aggregate(pipeline))
    
    # Convert datetime to ISO string for JSON serialization
    for activity in activities:
        if activity.get("created_at"):
            activity["created_at"] = activity["created_at"].isoformat()
    
    return jsonify({"activities": activities})
