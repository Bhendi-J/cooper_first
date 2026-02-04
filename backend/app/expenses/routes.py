from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from app.extensions import mongo
from app.utils.merkle_tree import EventMerkleTree, MerkleTree
from app.payments.services.finternet import FinternetService

expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/', methods=['POST'])
@jwt_required()
def add_expense():
    user_id = get_jwt_identity()
    data = request.get_json()
    event_id = ObjectId(data['event_id'])
    amount = data['amount']
    
    # Get event participants
    participants = list(mongo.db.participants.find(
        {"event_id": event_id, "status": "active"}
    ))
    
    if not participants:
        return jsonify({"error": "No active participants"}), 400
    
    # Calculate splits
    num_participants = len(participants)
    split_amount = amount / num_participants
    splits = []
    
    for p in participants:
        split = {
            "user_id": str(p['user_id']),
            "amount": split_amount,
            "status": "pending" if str(p['user_id']) != user_id else "paid"
        }
        splits.append(split)
    
    # Create expense
    expense = {
        "event_id": event_id,
        "payer_id": ObjectId(user_id),
        "amount": amount,
        "description": data['description'],
        "category_id": ObjectId(data.get('category_id')) if data.get('category_id') else None,
        "split_type": "equal",
        "splits": splits,
        "receipt_url": data.get('receipt_url'),
        "status": "pending",
        "merkle_hash": None,
        "created_at": datetime.utcnow()
    }
    
    result = mongo.db.expenses.insert_one(expense)
    expense['_id'] = str(result.inserted_id)
    expense['event_id'] = str(expense['event_id'])
    expense['payer_id'] = str(expense['payer_id'])
    if expense['category_id']:
        expense['category_id'] = str(expense['category_id'])
    
    # USP: Update Merkle tree
    all_expenses = list(mongo.db.expenses.find({"event_id": event_id}))
    merkle_tree = EventMerkleTree.build_event_tree(str(event_id), all_expenses)
    merkle_root = merkle_tree.get_root()
    
    # Update event with new merkle root
    mongo.db.events.update_one(
        {"_id": event_id},
        {
            "$set": {"merkle_root": merkle_root},
            "$inc": {"total_spent": amount}
        }
    )
    
    # Update participant balances
    for p in participants:
        balance_change = -split_amount if str(p['user_id']) != user_id else (amount - split_amount)
        mongo.db.participants.update_one(
            {"_id": p['_id']},
            {"$inc": {
                "balance": balance_change,
                "total_spent": split_amount if str(p['user_id']) != user_id else 0
            }}
        )
    
    # Create payment intents for non-payers
    finternet = FinternetService()
    payment_intents = []
    
    for split in splits:
        if split['status'] == 'pending':
            intent = finternet.create_payment_intent(
                amount=split['amount'],
                description=f"Split for: {data['description']}"
            )
            payment_intents.append({
                "user_id": split['user_id'],
                "intent": intent
            })
    
    return jsonify({
        "expense": expense,
        "merkle_root": merkle_root,
        "payment_intents": payment_intents
    })

@expenses_bp.route('/event/<event_id>', methods=['GET'])
@jwt_required()
def get_event_expenses(event_id):
    expenses = list(mongo.db.expenses.find({"event_id": ObjectId(event_id)}))
    
    # USP: Build Merkle tree for proofs
    all_expenses = list(mongo.db.expenses.find({"event_id": ObjectId(event_id)}))
    merkle_tree = EventMerkleTree.build_event_tree(event_id, all_expenses)
    
    result = []
    for i, expense in enumerate(expenses):
        expense['_id'] = str(expense['_id'])
        expense['event_id'] = str(expense['event_id'])
        expense['payer_id'] = str(expense['payer_id'])
        if expense.get('category_id'):
            expense['category_id'] = str(expense['category_id'])
        
        # USP: Add Merkle proof for each expense
        leaf = EventMerkleTree.expense_to_leaf(expense)
        expense['merkle_proof'] = merkle_tree.get_proof(i)
        expense['merkle_hash'] = merkle_tree.hash_data(leaf)
        result.append(expense)
    
    return jsonify({
        "expenses": result,
        "merkle_root": merkle_tree.get_root()
    })

@expenses_bp.route('/<expense_id>/verify', methods=['POST'])
@jwt_required()
def verify_expense(expense_id):
    data = request.get_json()
    
    expense = mongo.db.expenses.find_one({"_id": ObjectId(expense_id)})
    if not expense:
        return jsonify({"error": "Expense not found"}), 404
    
    event = mongo.db.events.find_one({"_id": expense["event_id"]})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Get stored Merkle root
    stored_root = event.get('merkle_root')
    
    # Verify proof
    leaf = EventMerkleTree.expense_to_leaf(expense)
    proof = data.get('proof', [])
    
    merkle_tree = MerkleTree()
    is_valid = merkle_tree.verify_proof(leaf, proof, stored_root)
    
    return jsonify({
        "valid": is_valid,
        "stored_root": stored_root,
        "expense_hash": merkle_tree.hash_data(leaf)
    })

@expenses_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    categories = list(mongo.db.categories.find())
    for cat in categories:
        cat['_id'] = str(cat['_id'])
    
    return jsonify({"categories": categories})