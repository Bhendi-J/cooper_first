from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from app.extensions import db as mongo

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

    return jsonify({
        "events": events_count,
        "expense_count": expense_count,
        "total_expense_amount": total_expense_amount
    })