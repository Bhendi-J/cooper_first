"""Analytics endpoints for dashboard charts and insights."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime, timedelta
from app.extensions import db as mongo

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/overview", methods=["GET"])
@jwt_required()
def overview():
    """
    Get analytics overview for the current user:
    - category_totals: Category-wise expense totals
    - daily_expenses: Daily expense aggregates for the last 30 days
    All computed via MongoDB aggregation (no frontend calculations).
    """
    uid = get_jwt_identity()
    user_oid = ObjectId(uid)
    
    # Get all event IDs user participates in
    participant_docs = list(mongo.participants.find({"user_id": user_oid}, {"event_id": 1}))
    event_ids = [p["event_id"] for p in participant_docs]
    
    if not event_ids:
        return jsonify({
            "category_totals": [],
            "daily_expenses": []
        })
    
    # Category-wise totals aggregation
    category_pipeline = [
        {"$match": {"event_id": {"$in": event_ids}}},
        {"$group": {
            "_id": "$category_id",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }},
        {"$lookup": {
            "from": "categories",
            "localField": "_id",
            "foreignField": "_id",
            "as": "category_info"
        }},
        {"$project": {
            "category_id": {"$toString": {"$ifNull": ["$_id", "uncategorized"]}},
            "category_name": {
                "$ifNull": [
                    {"$arrayElemAt": ["$category_info.name", 0]},
                    "Uncategorized"
                ]
            },
            "total": 1,
            "count": 1
        }},
        {"$sort": {"total": -1}}
    ]
    
    category_totals = list(mongo.expenses.aggregate(category_pipeline))
    
    # Daily expenses aggregation (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    daily_pipeline = [
        {"$match": {
            "event_id": {"$in": event_ids},
            "created_at": {"$gte": thirty_days_ago}
        }},
        {"$group": {
            "_id": {
                "$dateToString": {
                    "format": "%Y-%m-%d",
                    "date": "$created_at"
                }
            },
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},
        {"$project": {
            "date": "$_id",
            "total": 1,
            "count": 1,
            "_id": 0
        }}
    ]
    
    daily_expenses = list(mongo.expenses.aggregate(daily_pipeline))
    
    # Fill in missing dates with zero values for continuous chart
    date_map = {d["date"]: d for d in daily_expenses}
    filled_daily = []
    current_date = thirty_days_ago.date()
    end_date = datetime.utcnow().date()
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        if date_str in date_map:
            filled_daily.append(date_map[date_str])
        else:
            filled_daily.append({"date": date_str, "total": 0, "count": 0})
        current_date += timedelta(days=1)
    
    return jsonify({
        "category_totals": category_totals,
        "daily_expenses": filled_daily
    })
