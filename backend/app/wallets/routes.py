from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from app.extensions import mongo

wallets_bp = Blueprint('wallets', __name__)

@wallets_bp.route('/balance', methods=['GET'])
@jwt_required()
def get_wallet_balance():
    user_id = get_jwt_identity()
    
    # Get all participant records for the user
    participant_records = list(mongo.db.participants.find({"user_id": ObjectId(user_id)}))
    
    total_deposit = sum(p['deposit_amount'] for p in participant_records)
    total_balance = sum(p['balance'] for p in participant_records)
    
    return jsonify({
        "total_deposit": total_deposit,
        "current_balance": total_balance,
        "active_events": len(participant_records)
    })

@wallets_bp.route('/event/<event_id>/balance', methods=['GET'])
@jwt_required()
def get_event_wallet_balance(event_id):
    user_id = get_jwt_identity()
    
    participant = mongo.db.participants.find_one({
        "event_id": ObjectId(event_id),
        "user_id": ObjectId(user_id)
    })
    
    if not participant:
        return jsonify({"error": "Not a participant in this event"}), 404
    
    return jsonify({
        "deposit_amount": participant['deposit_amount'],
        "total_spent": participant['total_spent'],
        "balance": participant['balance']
    })