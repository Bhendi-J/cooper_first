# app/expenses/routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime

from app.extensions import db as mongo
from app.utils.merkle_tree import EventMerkleTree
from app.payments.services.finternet import FinternetService
from app.services.gemini_ocr import GeminiOCRService
from app.payments.models import SplitPaymentDB

expenses_bp = Blueprint("expenses", __name__)

@expenses_bp.route("/scan-receipt", methods=["POST"])
@jwt_required()
def scan_receipt():
    if 'receipt' not in request.files:
        return jsonify({"error": "No receipt file provided"}), 400
    
    file = request.files['receipt']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        image_bytes = file.read()
        ocr_service = GeminiOCRService()
        result = ocr_service.parse_receipt(image_bytes)
        
        if "error" in result:
             return jsonify(result), 400
             
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to scan receipt: {str(e)}"}), 500

@expenses_bp.route("/", methods=["POST"])
@jwt_required()
def add_expense():
    user_id = get_jwt_identity()
    data = request.get_json()

    event_id = ObjectId(data["event_id"])
    amount = float(data["amount"])
    description = data.get("description", "")
    category_id = data.get("category_id")

    participants = list(
        mongo.participants.find(
            {"event_id": event_id, "status": "active"}
        )
    )

    if not participants:
        return jsonify({"error": "No active participants"}), 400

    split_amount = round(amount / len(participants), 2)

    splits = []
    for p in participants:
        splits.append({
            "user_id": str(p["user_id"]),
            "amount": split_amount,
            "status": "paid" if str(p["user_id"]) == user_id else "pending"
        })

    expense = {
        "event_id": event_id,
        "payer_id": ObjectId(user_id),
        "amount": amount,
        "description": description,
        "category_id": ObjectId(category_id) if category_id else None,
        "split_type": "equal",
        "splits": splits,
        "status": "pending",
        "created_at": datetime.utcnow()
    }

    result = mongo.expenses.insert_one(expense)
    
    # Convert ObjectIds to strings for JSON response
    expense["_id"] = str(result.inserted_id)
    expense["event_id"] = str(expense["event_id"])
    expense["payer_id"] = str(expense["payer_id"])
    if expense["category_id"]:
        expense["category_id"] = str(expense["category_id"])
    expense["created_at"] = expense["created_at"].isoformat()

    # 🔐 Merkle Tree Update
    all_expenses = list(mongo.expenses.find({"event_id": event_id}))
    merkle_tree = EventMerkleTree.build_event_tree(str(event_id), all_expenses)
    merkle_root = merkle_tree.get_root()

    # Find the index of the newly added expense and get its proof
    expense_index = len(all_expenses) - 1  # New expense is the last one
    merkle_proof = merkle_tree.get_proof(expense_index)

    # Store the merkle proof with the expense
    mongo.expenses.update_one(
        {"_id": result.inserted_id},
        {"$set": {"merkle_proof": merkle_proof}}
    )
    expense["merkle_proof"] = merkle_proof

    # Update proofs for all other expenses since the tree changed
    for i, exp in enumerate(all_expenses[:-1]):  # Exclude the newly added one
        proof = merkle_tree.get_proof(i)
        mongo.expenses.update_one(
            {"_id": exp["_id"]},
            {"$set": {"merkle_proof": proof}}
        )

    mongo.events.update_one(
        {"_id": event_id},
        {
            "$set": {"merkle_root": merkle_root},
            "$inc": {"total_spent": amount}
        }
    )

    # Update participant balances
    for p in participants:
        if str(p["user_id"]) == user_id:
            balance_change = amount - split_amount
        else:
            balance_change = -split_amount

        mongo.participants.update_one(
            {"_id": p["_id"]},
            {
                "$inc": {
                    "balance": balance_change,
                    "total_spent": split_amount
                }
            }
        )

    # 💳 Create payment intents
    finternet = FinternetService()
    payment_intents = []

    for s in splits:
        if s["status"] == "pending":
            intent = finternet.create_payment_intent(
                amount=s["amount"],
                description=f"Split for {description}"
            )
            payment_intents.append({
                "user_id": s["user_id"],
                "intent": intent
            })

    # Log expense activity
    mongo.activities.insert_one({
        "type": "expense",
        "event_id": event_id,
        "user_id": ObjectId(user_id),
        "amount": amount,
        "description": description or "Expense",
        "expense_id": result.inserted_id,
        "created_at": datetime.utcnow()
    })

    # Save split payments to database for tracking
    try:
        SplitPaymentDB.create_for_expense(str(result.inserted_id), splits, payment_intents)
    except Exception as e:
        print(f"Failed to save split payments: {e}")

    return jsonify({
        "expense": expense,
        "merkle_root": merkle_root,
        "payment_intents": payment_intents
    }), 201

@expenses_bp.route("/event/<event_id>", methods=["GET"])
@jwt_required()
def get_event_expenses(event_id):
    event_id = ObjectId(event_id)
    expenses = list(mongo.expenses.find({"event_id": event_id}))

    merkle_tree = EventMerkleTree.build_event_tree(
        str(event_id), expenses
    )

    response = []
    for index, exp in enumerate(expenses):
        exp["_id"] = str(exp["_id"])
        exp["event_id"] = str(exp["event_id"])
        exp["payer_id"] = str(exp["payer_id"])

        leaf = EventMerkleTree.expense_to_leaf(exp)
        exp["merkle_hash"] = merkle_tree.hash_data(leaf)
        exp["merkle_proof"] = merkle_tree.get_proof(index)

        response.append(exp)

    return jsonify({
        "expenses": response,
        "merkle_root": merkle_tree.get_root()
    })

@expenses_bp.route("/categories", methods=["GET"])
@jwt_required()
def get_categories():
    categories = list(mongo.categories.find())
    for c in categories:
        c["_id"] = str(c["_id"])
    return jsonify({"categories": categories})

@expenses_bp.route("/<expense_id>/verify", methods=["POST"])
@jwt_required()
def verify_expense(expense_id):
    data = request.get_json()

    expense = mongo.expenses.find_one(
        {"_id": ObjectId(expense_id)}
    )
    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    event = mongo.events.find_one(
        {"_id": expense["event_id"]}
    )

    leaf = EventMerkleTree.expense_to_leaf(expense)
    stored_root = event.get("merkle_root") if event else None

    if not stored_root:
        return jsonify({
            "valid": False,
            "error": "No merkle root found for this event",
            "expense_hash": EventMerkleTree().hash_data(leaf)
        }), 400

    merkle_tree = EventMerkleTree()
    
    # Get proof from request or use stored proof
    data = request.get_json() or {}
    proof = data.get("proof")
    
    # If no proof in request, use the stored proof from the expense
    if proof is None:
        proof = expense.get("merkle_proof", [])
    
    valid = merkle_tree.verify_proof(leaf, proof, stored_root)

    return jsonify({
        "valid": valid,
        "stored_root": stored_root,
        "expense_hash": merkle_tree.hash_data(leaf),
        "proof_used": proof
    })
