from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from app.extensions import mongo
from app.payments.services.finternet import FinternetService

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/intents', methods=['POST'])
@jwt_required()
def create_intent():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    finternet = FinternetService()
    result = finternet.create_payment_intent(
        amount=data['amount'],
        currency=data.get('currency', 'USD'),
        description=f"Deposit for event: {data.get('event_name', 'Unknown')}",
        settlement_method=data.get('settlement_method', 'OFF_RAMP_MOCK'),
        settlement_destination=data.get('settlement_destination', 'test_account')
    )
    
    # Store intent in database
    payment_record = {
        "user_id": ObjectId(user_id),
        "event_id": ObjectId(data['event_id']) if data.get('event_id') else None,
        "intent_id": result.get('data', {}).get('id'),
        "amount": data['amount'],
        "currency": data.get('currency', 'USD'),
        "status": result.get('data', {}).get('status', 'INITIATED'),
        "payment_url": result.get('data', {}).get('paymentUrl'),
        "created_at": datetime.utcnow()
    }
    
    mongo.db.payments.insert_one(payment_record)
    
    return jsonify({
        "intent": result,
        "payment_url": result.get('data', {}).get('paymentUrl')
    })

@payments_bp.route('/intents/<intent_id>', methods=['GET'])
@jwt_required()
def get_intent_status(intent_id):
    finternet = FinternetService()
    result = finternet.get_payment_intent(intent_id)
    
    # Update status in database
    mongo.db.payments.update_one(
        {"intent_id": intent_id},
        {"$set": {
            "status": result.get('data', {}).get('status'),
            "updated_at": datetime.utcnow()
        }}
    )
    
    return jsonify(result)

@payments_bp.route('/intents/<intent_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_intent(intent_id):
    data = request.get_json()
    finternet = FinternetService()
    
    result = finternet.confirm_payment_intent(
        intent_id=intent_id,
        signature=data['signature'],
        payer_address=data['payer_address']
    )
    
    return jsonify(result)

@payments_bp.route('/webhook', methods=['POST'])
def payment_webhook():
    data = request.get_json()
    
    # Update payment status
    intent_id = data.get('data', {}).get('id')
    status = data.get('data', {}).get('status')
    
    if intent_id and status:
        mongo.db.payments.update_one(
            {"intent_id": intent_id},
            {"$set": {
                "status": status,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # If payment succeeded, update participant balance
        if status == 'SUCCEEDED':
            payment = mongo.db.payments.find_one({"intent_id": intent_id})
            if payment and payment.get('event_id'):
                mongo.db.participants.update_one(
                    {
                        "event_id": payment['event_id'],
                        "user_id": payment['user_id']
                    },
                    {
                        "$inc": {
                            "deposit_amount": payment['amount'],
                            "balance": payment['amount']
                        }
                    }
                )
    
    return jsonify({"status": "received"})