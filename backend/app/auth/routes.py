from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user

from app import bcrypt
from app.extensions import db
from app.users.model import User

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user_data = db.users.find_one({"email": email})
    if not user_data:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user_data["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    user = User(user_data)
    login_user(user, remember=True)
    
    # Debug: Print session info
    print(f"[LOGIN] User logged in: {email}")
    print(f"[LOGIN] Session: {dict(session)}")

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": str(user_data["_id"]),
            "email": user_data["email"]
        }
    })


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})


@auth.route("/me", methods=["GET"])
def get_current_user():
    # Debug: Print session and auth info
    print(f"[ME] Session: {dict(session)}")
    print(f"[ME] Is authenticated: {current_user.is_authenticated}")
    print(f"[ME] Request cookies: {request.cookies}")
    
    if current_user.is_authenticated:
        return jsonify({
            "user": {
                "id": current_user.id,
                "email": current_user.email
            }
        })
    return jsonify({"user": None}), 401
