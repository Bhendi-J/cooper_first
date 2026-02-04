from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from bson.errors import InvalidId

from app import bcrypt
from app.extensions import db

users = Blueprint("users", __name__)

# REGISTER USER
@users.route("/", methods=["POST"])
def register():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    if db.users.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 409

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

    result = db.users.insert_one({
        "email": email,
        "password": hashed_pw
    })

    return jsonify({
        "message": "User registered",
        "id": str(result.inserted_id)
    }), 201


# GET ALL USERS
@users.route("/all", methods=["GET"])
def get_all_users():
    users_list = [
        {
            "id": str(user["_id"]),
            "email": user["email"]
        }
        for user in db.users.find({}, {"email": 1})
    ]
    return jsonify(users_list)


# GET SINGLE USER
@users.route("/<user_id>", methods=["GET"])
def get_user(user_id):
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)}, {"email": 1})
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "id": str(user["_id"]),
            "email": user["email"]
        })

    except InvalidId:
        return jsonify({"error": "Invalid ID"}), 400