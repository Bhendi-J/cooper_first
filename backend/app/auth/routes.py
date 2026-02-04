from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from bcrypt import hashpw, gensalt, checkpw
from app.extensions import mongo
from datetime import datetime
from bson import ObjectId

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({"error": "Missing required fields"}), 400
    
    if mongo.db.users.find_one({"email": data['email']}):
        return jsonify({"error": "User already exists"}), 409
    
    password_hash = hashpw(data['password'].encode('utf-8'), gensalt())
    
    user = {
        "name": data['name'],
        "email": data['email'],
        "password_hash": password_hash,
        "phone": data.get('phone'),
        "wallet_address": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = mongo.db.users.insert_one(user)
    user['_id'] = str(result.inserted_id)
    del user['password_hash']
    
    access_token = create_access_token(identity=user['_id'])
    
    return jsonify({
        "access_token": access_token,
        "user": user
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    user = mongo.db.users.find_one({"email": data.get('email')})
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    
    if not checkpw(data['password'].encode('utf-8'), user['password_hash']):
        return jsonify({"error": "Invalid credentials"}), 401
    
    access_token = create_access_token(identity=str(user['_id']))
    
    return jsonify({
        "access_token": access_token,
        "user": {
            "_id": str(user['_id']),
            "name": user['name'],
            "email": user['email'],
            "phone": user.get('phone'),
            "wallet_address": user.get('wallet_address')
        }
    })

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "_id": str(user['_id']),
        "name": user['name'],
        "email": user['email'],
        "phone": user.get('phone'),
        "wallet_address": user.get('wallet_address')
    })