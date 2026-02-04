from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from app.extensions import mongo
from app.payments.services.finternet import FinternetService

settlements_bp = Blueprint('settlements', __name__)

@settlements_bp.route('/events/<event_id>/close', methods=['POST'])
@jwt_required()
def close_event(event_id):
    user_id = get_jwt_identity()
    
    # Verify creator
    event = mongo.db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    if str(event['creator_id']) != user_id:
        return jsonify({"error": "Only creator can close event"}), 403
    
    # Get all participants with balances
    participants = list(mongo.db.participants.find({"event_id": ObjectId(event_id)}))
    settlements = []
    finternet = FinternetService()
    
    for p in participants:
        balance = p['balance']
        
        if balance > 0:
            # Refund excess to user
            settlement_type = "refund"
            intent = finternet.create_payment_intent(
                amount=balance,
                description=f"Refund from event: {event['name']}"
            )
        elif balance < 0:
            # Collect owed amount
            settlement_type = "collection"
            intent = finternet.create_payment_intent(
                amount=abs(balance),
                description=f"Payment for event: {event['name']}"
            )
        else:
            settlement_type = "none"
            intent = None
        
        settlement = {
            "event_id": ObjectId(event_id),
            "participant_id": p['_id'],
            "user_id": p['user_id'],
            "amount": abs(balance),
            "type": settlement_type,
            "status": "pending" if intent else "completed",
            "payment_intent_id": intent.get('data', {}).get('id') if intent else None,
            "created_at": datetime.utcnow()
        }
        
        mongo.db.settlements.insert_one(settlement)
        settlements.append(settlement)
    
    # Update event status
    mongo.db.events.update_one(
        {"_id": ObjectId(event_id)},
        {"$set": {
            "status": "completed",
            "closed_at": datetime.utcnow()
        }}
    )
    
    return jsonify({
        "event_id": event_id,
        "status": "closed",
        "settlements": settlements
    })

@settlements_bp.route('/events/<event_id>/report', methods=['GET'])
@jwt_required()
def get_settlement_report(event_id):
    event = mongo.db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    participants = list(mongo.db.participants.find({"event_id": ObjectId(event_id)}))
    expenses = list(mongo.db.expenses.find({"event_id": ObjectId(event_id)}))
    settlements = list(mongo.db.settlements.find({"event_id": ObjectId(event_id)}))
    
    # Calculate totals
    total_deposits = sum(p['deposit_amount'] for p in participants)
    total_spent = sum(e['amount'] for e in expenses)
    
    return jsonify({
        "event": {
            "id": str(event['_id']),
            "name": event['name'],
            "status": event['status'],
            "merkle_root": event.get('merkle_root')
        },
        "summary": {
            "total_deposits": total_deposits,
            "total_spent": total_spent,
            "remaining": total_deposits - total_spent,
            "participant_count": len(participants),
            "expense_count": len(expenses)
        },
        "participants": [{
            "user_id": str(p['user_id']),
            "deposit": p['deposit_amount'],
            "spent": p['total_spent'],
            "balance": p['balance']
        } for p in participants],
        "settlements": [{
            "user_id": str(s['user_id']),
            "amount": s['amount'],
            "type": s['type'],
            "status": s['status']
        } for s in settlements]
    })