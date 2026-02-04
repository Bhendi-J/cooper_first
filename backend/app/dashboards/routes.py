from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime, timedelta
from app.extensions import mongo

dashboards_bp = Blueprint('dashboards', __name__)

@dashboards_bp.route('/user-summary', methods=['GET'])
@jwt_required()
def get_user_summary():
    user_id = get_jwt_identity()
    
    # Get user's events
    participant_records = list(mongo.db.participants.find({"user_id": ObjectId(user_id)}))
    event_ids = [p['event_id'] for p in participant_records]
    
    # Calculate totals
    total_deposited = sum(p['deposit_amount'] for p in participant_records)
    total_spent = sum(p['total_spent'] for p in participant_records)
    current_balance = sum(p['balance'] for p in participant_records)
    
    # Get active events count
    active_events = mongo.db.events.count_documents({
        "_id": {"$in": event_ids},
        "status": "active"
    })
    
    # Get spending by category
    pipeline = [
        {"$match": {"payer_id": ObjectId(user_id)}},
        {"$group": {
            "_id": "$category_id",
            "total": {"$sum": "$amount"}
        }}
    ]
    category_spending = list(mongo.db.expenses.aggregate(pipeline))
    
    # Get recent expenses
    recent_expenses = list(mongo.db.expenses.find(
        {"payer_id": ObjectId(user_id)}
    ).sort("created_at", -1).limit(5))
    
    for expense in recent_expenses:
        expense['_id'] = str(expense['_id'])
        expense['event_id'] = str(expense['event_id'])
        expense['payer_id'] = str(expense['payer_id'])
    
    return jsonify({
        "summary": {
            "total_deposited": total_deposited,
            "total_spent": total_spent,
            "current_balance": current_balance,
            "active_events": active_events
        },
        "category_spending": category_spending,
        "recent_expenses": recent_expenses
    })

@dashboards_bp.route('/events/<event_id>/analytics', methods=['GET'])
@jwt_required()
def get_event_analytics(event_id):
    # Get event details
    event = mongo.db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Get expenses by category
    pipeline = [
        {"$match": {"event_id": ObjectId(event_id)}},
        {"$group": {
            "_id": "$category_id",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]
    category_stats = list(mongo.db.expenses.aggregate(pipeline))
    
    # Get daily spending
    daily_pipeline = [
        {"$match": {"event_id": ObjectId(event_id)}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_spending = list(mongo.db.expenses.aggregate(daily_pipeline))
    
    return jsonify({
        "event": {
            "id": str(event['_id']),
            "name": event['name'],
            "total_pool": event.get('total_pool', 0),
            "total_spent": event.get('total_spent', 0)
        },
        "category_stats": category_stats,
        "daily_spending": daily_spending
    })