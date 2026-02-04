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

    events = mongo.participants.count_documents({"user_id": uid})
    expenses = mongo.expenses.count_documents({"payer_id": uid})

    return jsonify({
        "events": events,
        "expenses": expenses
    })