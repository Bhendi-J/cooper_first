from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from bcrypt import hashpw, gensalt, checkpw
from datetime import datetime
from bson import ObjectId
from app.extensions import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not all(k in data for k in ("name", "email", "password")):
        return jsonify({"error": "Missing required fields"}), 400

    if db.users.find_one({"email": data["email"]}):
        return jsonify({"error": "User already exists"}), 409

    password_hash = hashpw(data["password"].encode(), gensalt())

    user = {
        "name": data["name"],
        "email": data["email"],
        "password_hash": password_hash,
        "created_at": datetime.utcnow(),
        "wallet_address": None
    }

    res = db.users.insert_one(user)
    access_token = create_access_token(identity=str(res.inserted_id))

    return jsonify({
        "access_token": access_token,
        "user": {
            "_id": str(res.inserted_id),
            "name": user["name"],
            "email": user["email"]
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = db.users.find_one({"email": data.get("email")})

    if not user or not checkpw(data["password"].encode(), user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user["_id"]))

    return jsonify({
        "access_token": token,
        "user": {
            "_id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"]
        }
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    uid = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(uid)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "_id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "wallet_address": user.get("wallet_address")
    })