"""Analytics endpoints for dashboard charts and insights."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime, timedelta
from app.extensions import db as mongo

analytics_bp = Blueprint("analytics", __name__)

# Default expense categories with icons and colors
DEFAULT_CATEGORIES = {
    "food": {"name": "Food & Dining", "icon": "🍔", "color": "#FF6B6B"},
    "transport": {"name": "Transport", "icon": "🚗", "color": "#4ECDC4"},
    "entertainment": {"name": "Entertainment", "icon": "🎬", "color": "#45B7D1"},
    "shopping": {"name": "Shopping", "icon": "🛍️", "color": "#96CEB4"},
    "utilities": {"name": "Utilities", "icon": "💡", "color": "#FFEAA7"},
    "travel": {"name": "Travel", "icon": "✈️", "color": "#DDA0DD"},
    "health": {"name": "Health", "icon": "💊", "color": "#98D8C8"},
    "groceries": {"name": "Groceries", "icon": "🛒", "color": "#F7DC6F"},
    "accommodation": {"name": "Accommodation", "icon": "🏨", "color": "#BB8FCE"},
    "other": {"name": "Other", "icon": "📦", "color": "#85C1E9"},
}


def categorize_expense(description: str) -> str:
    """Auto-categorize expense based on description keywords."""
    desc_lower = description.lower() if description else ""
    
    food_keywords = ['food', 'lunch', 'dinner', 'breakfast', 'restaurant', 'cafe', 'coffee', 'pizza', 'burger', 'meal', 'snack', 'drinks', 'bar']
    transport_keywords = ['uber', 'ola', 'cab', 'taxi', 'bus', 'metro', 'fuel', 'petrol', 'diesel', 'parking', 'toll']
    entertainment_keywords = ['movie', 'concert', 'show', 'game', 'netflix', 'spotify', 'subscription', 'party']
    shopping_keywords = ['amazon', 'flipkart', 'shop', 'clothes', 'shoes', 'electronics', 'gadget']
    travel_keywords = ['flight', 'hotel', 'airbnb', 'trip', 'vacation', 'booking', 'train', 'ticket']
    health_keywords = ['medicine', 'doctor', 'hospital', 'pharmacy', 'gym', 'fitness']
    groceries_keywords = ['grocery', 'supermarket', 'vegetables', 'fruits', 'milk', 'bread']
    accommodation_keywords = ['rent', 'stay', 'hostel', 'lodge', 'room']
    utilities_keywords = ['electricity', 'water', 'gas', 'internet', 'phone', 'bill', 'recharge']
    
    if any(kw in desc_lower for kw in food_keywords):
        return "food"
    elif any(kw in desc_lower for kw in transport_keywords):
        return "transport"
    elif any(kw in desc_lower for kw in entertainment_keywords):
        return "entertainment"
    elif any(kw in desc_lower for kw in shopping_keywords):
        return "shopping"
    elif any(kw in desc_lower for kw in travel_keywords):
        return "travel"
    elif any(kw in desc_lower for kw in health_keywords):
        return "health"
    elif any(kw in desc_lower for kw in groceries_keywords):
        return "groceries"
    elif any(kw in desc_lower for kw in accommodation_keywords):
        return "accommodation"
    elif any(kw in desc_lower for kw in utilities_keywords):
        return "utilities"
    return "other"


@analytics_bp.route("/overview", methods=["GET"])
@jwt_required()
def overview():
    """
    Get analytics overview for the current user:
    - category_totals: Category-wise expense totals with colors and icons
    - daily_expenses: Daily expense aggregates for the last 30 days
    - weekly_comparison: This week vs last week
    - top_events: Top spending events
    - monthly_trend: Monthly totals for the last 6 months
    """
    uid = get_jwt_identity()
    user_oid = ObjectId(uid)
    
    # Get all event IDs user participates in
    participant_docs = list(mongo.participants.find({"user_id": user_oid}, {"event_id": 1}))
    event_ids = [p["event_id"] for p in participant_docs]
    
    if not event_ids:
        return jsonify({
            "category_totals": [],
            "daily_expenses": [],
            "weekly_comparison": {"this_week": 0, "last_week": 0, "change_percent": 0},
            "top_events": [],
            "monthly_trend": [],
            "total_expenses": 0,
            "avg_expense": 0
        })
    
    # Get all expenses for categorization
    all_expenses = list(mongo.expenses.find({
        "event_id": {"$in": event_ids},
        "status": {"$in": ["approved", "verified", "pending"]}
    }))
    
    # Auto-categorize and aggregate by category
    category_aggregates = {}
    for exp in all_expenses:
        category = categorize_expense(exp.get("description", ""))
        if category not in category_aggregates:
            category_aggregates[category] = {"total": 0, "count": 0}
        category_aggregates[category]["total"] += float(exp.get("amount", 0))
        category_aggregates[category]["count"] += 1
    
    # Build category totals with metadata
    category_totals = []
    for cat_key, data in sorted(category_aggregates.items(), key=lambda x: x[1]["total"], reverse=True):
        cat_info = DEFAULT_CATEGORIES.get(cat_key, DEFAULT_CATEGORIES["other"])
        category_totals.append({
            "category_id": cat_key,
            "category_name": cat_info["name"],
            "icon": cat_info["icon"],
            "color": cat_info["color"],
            "total": round(data["total"], 2),
            "count": data["count"]
        })
    
    # Daily expenses aggregation (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    daily_pipeline = [
        {"$match": {
            "event_id": {"$in": event_ids},
            "created_at": {"$gte": thirty_days_ago},
            "status": {"$in": ["approved", "verified", "pending"]}
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
    
    # Fill in missing dates with zero values
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
    
    # Weekly comparison (this week vs last week)
    today = datetime.utcnow()
    start_of_this_week = today - timedelta(days=today.weekday())
    start_of_last_week = start_of_this_week - timedelta(days=7)
    
    this_week_total = sum(
        float(e.get("amount", 0)) for e in all_expenses
        if e.get("created_at") and e["created_at"] >= start_of_this_week
    )
    
    last_week_total = sum(
        float(e.get("amount", 0)) for e in all_expenses
        if e.get("created_at") and start_of_last_week <= e["created_at"] < start_of_this_week
    )
    
    change_percent = 0
    if last_week_total > 0:
        change_percent = round(((this_week_total - last_week_total) / last_week_total) * 100, 1)
    
    # Top events by spending
    event_spending = {}
    for exp in all_expenses:
        eid = str(exp["event_id"])
        event_spending[eid] = event_spending.get(eid, 0) + float(exp.get("amount", 0))
    
    # Get event names
    top_event_ids = sorted(event_spending.keys(), key=lambda x: event_spending[x], reverse=True)[:5]
    top_events = []
    for eid in top_event_ids:
        event = mongo.events.find_one({"_id": ObjectId(eid)})
        if event:
            top_events.append({
                "event_id": eid,
                "event_name": event.get("name", "Unknown"),
                "total": round(event_spending[eid], 2)
            })
    
    # Monthly trend (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_pipeline = [
        {"$match": {
            "event_id": {"$in": event_ids},
            "created_at": {"$gte": six_months_ago},
            "status": {"$in": ["approved", "verified", "pending"]}
        }},
        {"$group": {
            "_id": {
                "$dateToString": {
                    "format": "%Y-%m",
                    "date": "$created_at"
                }
            },
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},
        {"$project": {
            "month": "$_id",
            "total": 1,
            "count": 1,
            "_id": 0
        }}
    ]
    
    monthly_trend = list(mongo.expenses.aggregate(monthly_pipeline))
    
    # Compute totals
    total_expenses = sum(float(e.get("amount", 0)) for e in all_expenses)
    avg_expense = total_expenses / len(all_expenses) if all_expenses else 0
    
    return jsonify({
        "category_totals": category_totals,
        "daily_expenses": filled_daily,
        "weekly_comparison": {
            "this_week": round(this_week_total, 2),
            "last_week": round(last_week_total, 2),
            "change_percent": change_percent
        },
        "top_events": top_events,
        "monthly_trend": monthly_trend,
        "total_expenses": round(total_expenses, 2),
        "avg_expense": round(avg_expense, 2),
        "expense_count": len(all_expenses)
    })
