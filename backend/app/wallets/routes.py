"""Wallet routes for personal wallet management."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime

from app.extensions import db as mongo
from app.core import WalletFallbackService, NotificationService

bp = Blueprint("wallets", __name__)


@bp.route("/balance", methods=["GET"])
@jwt_required()
def get_balance():
    """Get current user's wallet balance."""
    user_id = get_jwt_identity()
    
    balance = WalletFallbackService.get_wallet_balance(user_id)
    
    return jsonify({
        "user_id": user_id,
        "balance": balance
    })


@bp.route("/balance/<user_id>", methods=["GET"])
@jwt_required()
def get_user_balance(user_id):
    """Get a specific user's wallet balance (admin/participant view)."""
    current_user = get_jwt_identity()
    
    # Allow viewing own balance or if admin
    if current_user != user_id:
        # Could add admin check here
        pass
    
    balance = WalletFallbackService.get_wallet_balance(user_id)
    
    return jsonify({
        "user_id": user_id,
        "balance": balance
    })


@bp.route("/deposit", methods=["POST"])
@jwt_required()
def deposit():
    """
    Top up wallet balance (requires payment integration).
    
    Request body:
    {
        "amount": 100.00
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    amount = data.get("amount")
    if not amount or float(amount) <= 0:
        return jsonify({"error": "Valid amount required"}), 400
    
    amount = float(amount)
    
    # Credit the wallet
    success, new_balance = WalletFallbackService.credit_wallet(
        user_id=user_id,
        amount=amount,
        source="topup",
        notes="Direct wallet top-up"
    )
    
    if success:
        # Send notification
        NotificationService.notify_payment_confirmed(
            user_id=user_id,
            amount=amount,
            purpose="Wallet top-up"
        )
        
        return jsonify({
            "status": "ok",
            "message": f"Wallet credited with ${amount:.2f}",
            "new_balance": new_balance
        }), 201
    else:
        return jsonify({"error": "Failed to credit wallet"}), 500


@bp.route("/withdraw", methods=["POST"])
@jwt_required()
def withdraw():
    """
    Withdraw from wallet.
    
    Request body:
    {
        "amount": 50.00
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    amount = data.get("amount")
    if not amount or float(amount) <= 0:
        return jsonify({"error": "Valid amount required"}), 400
    
    amount = float(amount)
    
    success, error, amount_debited = WalletFallbackService.debit_wallet(
        user_id=user_id,
        amount=amount,
        purpose="withdrawal",
        notes="Wallet withdrawal"
    )
    
    if success:
        new_balance = WalletFallbackService.get_wallet_balance(user_id)
        return jsonify({
            "status": "ok",
            "message": f"${amount:.2f} withdrawn from wallet",
            "amount_withdrawn": amount_debited,
            "new_balance": new_balance
        })
    else:
        return jsonify({"error": error}), 400


@bp.route("/transactions", methods=["GET"])
@jwt_required()
def get_transactions():
    """Get wallet transaction history."""
    user_id = get_jwt_identity()
    
    # Get pagination params
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    skip = (page - 1) * per_page
    
    # Get transactions
    transactions = list(
        mongo.wallet_transactions.find({"user_id": ObjectId(user_id)})
        .sort("created_at", -1)
        .skip(skip)
        .limit(per_page)
    )
    
    # Count total
    total = mongo.wallet_transactions.count_documents({"user_id": ObjectId(user_id)})
    
    # Format response
    for tx in transactions:
        tx["_id"] = str(tx["_id"])
        tx["wallet_id"] = str(tx["wallet_id"])
        tx["user_id"] = str(tx["user_id"])
        if tx.get("created_at"):
            tx["created_at"] = tx["created_at"].isoformat()
    
    return jsonify({
        "transactions": transactions,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page
    })


@bp.route("/transfer", methods=["POST"])
@jwt_required()
def transfer():
    """
    Transfer from wallet to another user.
    
    Request body:
    {
        "to_user_id": "...",
        "amount": 25.00,
        "notes": "optional note"
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    to_user_id = data.get("to_user_id")
    amount = data.get("amount")
    notes = data.get("notes", "")
    
    if not to_user_id or not amount:
        return jsonify({"error": "to_user_id and amount required"}), 400
    
    if user_id == to_user_id:
        return jsonify({"error": "Cannot transfer to yourself"}), 400
    
    amount = float(amount)
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400
    
    # Verify recipient exists
    recipient = mongo.users.find_one({"_id": ObjectId(to_user_id)})
    if not recipient:
        return jsonify({"error": "Recipient not found"}), 404
    
    # Debit sender
    success, error, _ = WalletFallbackService.debit_wallet(
        user_id=user_id,
        amount=amount,
        purpose="transfer_out",
        reference_id=to_user_id,
        notes=f"Transfer to {recipient.get('name', 'User')}: {notes}"
    )
    
    if not success:
        return jsonify({"error": error}), 400
    
    # Credit recipient
    sender = mongo.users.find_one({"_id": ObjectId(user_id)})
    WalletFallbackService.credit_wallet(
        user_id=to_user_id,
        amount=amount,
        source="transfer_in",
        reference_id=user_id,
        notes=f"Transfer from {sender.get('name', 'User')}: {notes}"
    )
    
    # Notify both parties
    NotificationService.create_notification(
        user_id=to_user_id,
        notification_type="transfer_received",
        title="Transfer Received",
        message=f"You received ${amount:.2f} from {sender.get('name', 'a user')}",
        data={"from_user_id": user_id, "amount": amount}
    )
    
    new_balance = WalletFallbackService.get_wallet_balance(user_id)
    
    return jsonify({
        "status": "ok",
        "message": f"${amount:.2f} transferred successfully",
        "new_balance": new_balance
    })

