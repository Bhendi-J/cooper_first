"""
Wellness API Routes - A supportive financial wellness companion.

These endpoints provide non-judgmental financial insights and gentle reminders.
All data is private to the user - never shared or used for restrictions.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

from app.services.financial_wellness import get_wellness_service
from app.extensions import db as mongo

wellness_bp = Blueprint("wellness", __name__)


@wellness_bp.route("/summary", methods=["GET"])
@jwt_required()
def get_wellness_summary():
    """
    Get your personalized financial wellness summary.
    
    Returns:
    - Wellness score (focuses on positive behaviors)
    - Spending insights (non-judgmental)
    - Pending settlements (with no-pressure messaging)
    - Category breakdown
    - Encouraging insights and tips
    
    This data is private to you and never affects your access to features.
    """
    user_id = get_jwt_identity()
    
    try:
        wellness_service = get_wellness_service(mongo)
        summary = wellness_service.get_user_wellness_summary(user_id)
        
        return jsonify({
            "summary": summary,
            "privacy_note": "This information is private to you and never shared with others."
        }), 200
        
    except Exception as e:
        print(f"Error getting wellness summary: {e}")
        return jsonify({
            "error": "Unable to load wellness summary",
            "fallback": {
                "wellness_score": 70,
                "wellness_status": {
                    "label": "Doing Well",
                    "emoji": "✨",
                    "color": "blue",
                    "description": "Keep up the good work!"
                },
                "encouragement": "You're doing great! 🌟"
            }
        }), 200  # Return 200 with fallback data - never block users


@wellness_bp.route("/reminders", methods=["GET"])
@jwt_required()
def get_reminders():
    """
    Get gentle, dismissible reminders about pending settlements.
    
    These are NEVER urgent and always framed positively.
    Users can dismiss any reminder - we respect your preferences.
    """
    user_id = get_jwt_identity()
    
    try:
        wellness_service = get_wellness_service(mongo)
        reminders = wellness_service.get_gentle_reminders(user_id, max_reminders=3)
        
        return jsonify({
            "reminders": reminders,
            "message": "These are just friendly nudges - dismiss anytime!"
        }), 200
        
    except Exception as e:
        print(f"Error getting reminders: {e}")
        return jsonify({"reminders": [], "message": "No reminders right now!"}), 200


@wellness_bp.route("/dismiss-reminder", methods=["POST"])
@jwt_required()
def dismiss_reminder():
    """
    Dismiss a reminder - we won't show it again.
    We respect your preferences.
    """
    from flask import request
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    reminder_type = data.get("reminder_type")
    reference_id = data.get("reference_id")  # event_id, expense_id, etc.
    
    if not reminder_type:
        return jsonify({"error": "reminder_type required"}), 400
    
    try:
        # Store dismissed reminders
        mongo.dismissed_reminders.update_one(
            {
                "user_id": ObjectId(user_id),
                "reminder_type": reminder_type,
                "reference_id": reference_id
            },
            {
                "$set": {
                    "dismissed_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return jsonify({"message": "Reminder dismissed. We won't show it again."}), 200
        
    except Exception as e:
        print(f"Error dismissing reminder: {e}")
        return jsonify({"error": "Failed to dismiss reminder"}), 500


@wellness_bp.route("/spending-breakdown", methods=["GET"])
@jwt_required()
def get_spending_breakdown():
    """
    Get a detailed breakdown of your spending by category.
    
    This helps you understand where your money goes - 
    no judgment, just insights.
    """
    from flask import request
    from datetime import datetime, timedelta
    
    user_id = get_jwt_identity()
    
    # Optional: days parameter (default 30)
    days = request.args.get("days", 30, type=int)
    days = min(max(days, 7), 365)  # Between 7 and 365 days
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get expenses where user paid
        expenses = list(mongo.expenses.find({
            "payer_id": ObjectId(user_id),
            "created_at": {"$gte": cutoff_date}
        }))
        
        # Calculate totals by category
        category_totals = {}
        total_amount = 0
        
        category_emoji = {
            "food": "🍕",
            "transport": "🚗",
            "entertainment": "🎬",
            "shopping": "🛍️",
            "utilities": "💡",
            "health": "💊",
            "travel": "✈️",
            "other": "📦"
        }
        
        for exp in expenses:
            category = exp.get("category", "other")
            if isinstance(category, ObjectId):
                # Lookup category name
                cat_doc = mongo.categories.find_one({"_id": category})
                category = cat_doc.get("name", "other").lower() if cat_doc else "other"
            
            amount = exp.get("amount", 0)
            category_totals[category] = category_totals.get(category, 0) + amount
            total_amount += amount
        
        # Build breakdown with percentages
        breakdown = []
        for category, amount in sorted(category_totals.items(), key=lambda x: -x[1]):
            percentage = (amount / total_amount * 100) if total_amount > 0 else 0
            breakdown.append({
                "category": category,
                "emoji": category_emoji.get(category, "📦"),
                "amount": round(amount, 2),
                "percentage": round(percentage, 1),
                "transaction_count": len([e for e in expenses if (e.get("category") or "other") == category])
            })
        
        # Insights
        insights = []
        if breakdown:
            top_category = breakdown[0]
            insights.append({
                "type": "info",
                "icon": top_category["emoji"],
                "message": f"Most of your spending ({top_category['percentage']}%) goes to {top_category['category']}."
            })
        
        if total_amount > 0:
            avg_per_day = total_amount / days
            insights.append({
                "type": "info",
                "icon": "📊",
                "message": f"You average about ₹{avg_per_day:.0f} per day in group expenses."
            })
        
        return jsonify({
            "period_days": days,
            "total_spent": round(total_amount, 2),
            "transaction_count": len(expenses),
            "breakdown": breakdown,
            "insights": insights
        }), 200
        
    except Exception as e:
        print(f"Error getting spending breakdown: {e}")
        return jsonify({
            "error": "Unable to load spending breakdown",
            "breakdown": []
        }), 200


# Import datetime for dismiss_reminder
from datetime import datetime
