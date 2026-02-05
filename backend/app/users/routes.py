from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from app.extensions import db as mongo
import re

users_bp = Blueprint("users", __name__)

@users_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    uid = get_jwt_identity()
    user = mongo.users.find_one({"_id": ObjectId(uid)}, {"password_hash": 0})

    if not user:
        return jsonify({"error": "User not found"}), 404

    user["_id"] = str(user["_id"])
    return jsonify(user)


@users_bp.route("/summary", methods=["GET"])
@jwt_required()
def summary():
    uid = get_jwt_identity()
    user_oid = ObjectId(uid)

    # Count events user participates in
    events_count = mongo.participants.count_documents({"user_id": user_oid})
    
    # Count expenses added by user
    expense_count = mongo.expenses.count_documents({"payer_id": user_oid})
    
    # Aggregate total expense amount for expenses added by user
    total_expense_pipeline = [
        {"$match": {"payer_id": user_oid}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    total_expense_result = list(mongo.expenses.aggregate(total_expense_pipeline))
    total_expense_amount = total_expense_result[0]["total"] if total_expense_result else 0
    
    # Get user's balance across all events (sum of participant balances)
    # This reflects deposits minus their share of expenses
    balance_pipeline = [
        {"$match": {"user_id": user_oid}},
        {"$group": {
            "_id": None, 
            "total_balance": {"$sum": "$balance"},
            "total_deposits": {"$sum": "$deposit_amount"}
        }}
    ]
    balance_result = list(mongo.participants.aggregate(balance_pipeline))
    total_balance = balance_result[0]["total_balance"] if balance_result else 0
    total_deposits = balance_result[0]["total_deposits"] if balance_result else 0
    
    # Calculate net position (positive = owed money, negative = owes money)
    net_position = round(total_balance, 2)

    return jsonify({
        "events": events_count,
        "expense_count": expense_count,
        "total_expense_amount": round(total_expense_amount, 2),
        "total_balance": round(total_balance, 2),
        "total_deposits": round(total_deposits, 2),
        "net_position": net_position
    })


@users_bp.route("/search", methods=["GET"])
@jwt_required()
def search_users():
    """Search for users by email or name."""
    query = request.args.get("q", "").strip()
    current_user_id = get_jwt_identity()
    
    if not query:
        return jsonify({"users": []})
    
    if len(query) < 2:
        return jsonify({"users": []})
    
    # Create regex for case-insensitive search
    regex_pattern = re.compile(re.escape(query), re.IGNORECASE)
    
    # Search by email or name, excluding current user
    users = list(mongo.users.find(
        {
            "_id": {"$ne": ObjectId(current_user_id)},
            "$or": [
                {"email": regex_pattern},
                {"name": regex_pattern}
            ]
        },
        {"_id": 1, "name": 1, "email": 1}
    ).limit(10))
    
    # Format response
    for user in users:
        user["_id"] = str(user["_id"])
    
    return jsonify({"users": users})