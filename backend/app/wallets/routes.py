"""Wallet routes for personal wallet management."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime

from app.extensions import db as mongo
from app.core import WalletFallbackService, NotificationService
from app.payments.services.finternet import FinternetService

bp = Blueprint("wallets", __name__)

# Company fee percentage for withdrawals (1% donation)
WITHDRAWAL_FEE_PERCENT = 0.01


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
    Wallet deposit via Finternet payment gateway.
    
    Credits wallet immediately before redirecting to payment gateway.
    
    Request body:
    {
        "amount": 100.00,
        "use_finternet": true  // optional, defaults to true
    }
    
    Returns payment intent with URL to complete payment.
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    amount = data.get("amount")
    if not amount or float(amount) <= 0:
        return jsonify({"error": "Valid amount required"}), 400
    
    amount = float(amount)
    use_finternet = data.get("use_finternet", True)
    
    # Credit the wallet IMMEDIATELY (before payment gateway redirect)
    success, new_balance = WalletFallbackService.credit_wallet(
        user_id=user_id,
        amount=amount,
        source="finternet_topup",
        notes=f"Wallet top-up via Finternet"
    )
    
    if not success:
        return jsonify({"error": "Failed to credit wallet"}), 500
    
    if use_finternet:
        try:
            # Create Finternet payment intent (for record keeping)
            finternet = FinternetService()
            
            intent_response = finternet.create_payment_intent(
                amount=str(amount),
                currency="USD",
                description=f"Wallet top-up for user {user_id}"
            )
            
            intent_data = intent_response.get("data", intent_response)
            intent_id = intent_data.get("id") or intent_response.get("id")
            
            # Store deposit record (already completed)
            mongo.wallet_deposits.insert_one({
                "user_id": ObjectId(user_id),
                "intent_id": intent_id,
                "amount": amount,
                "status": "completed",
                "new_balance": new_balance,
                "created_at": datetime.utcnow()
            })
            
            # Get payment URL
            payment_url = finternet.get_payment_url(intent_response)
            
            return jsonify({
                "status": "ok",
                "message": f"Wallet credited with ${amount:.2f}",
                "intent_id": intent_id,
                "payment_url": payment_url,
                "amount": amount,
                "new_balance": new_balance
            }), 201
            
        except Exception as e:
            # Payment intent creation failed but wallet was already credited
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "ok",
                "message": f"Wallet credited with ${amount:.2f}",
                "amount": amount,
                "new_balance": new_balance,
                "payment_url": None
            }), 201
    else:
        return jsonify({
            "status": "ok",
            "message": f"Wallet credited with ${amount:.2f}",
            "new_balance": new_balance,
            "amount": amount
        }), 201


@bp.route("/deposit/confirm", methods=["POST"])
@jwt_required()
def confirm_deposit():
    """
    Confirm a wallet deposit after Finternet payment is completed.
    
    Request body:
    {
        "intent_id": "intent_xxx"
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    intent_id = data.get("intent_id")
    if not intent_id:
        return jsonify({"error": "Intent ID required"}), 400
    
    try:
        # Check if deposit already processed
        existing = mongo.pending_wallet_deposits.find_one({
            "intent_id": intent_id,
            "user_id": ObjectId(user_id)
        })
        
        if not existing:
            return jsonify({"error": "Deposit not found"}), 404
        
        if existing.get("status") == "completed":
            return jsonify({"error": "Deposit already processed"}), 400
        
        # Verify payment with Finternet
        finternet = FinternetService()
        intent_result = finternet.get_payment_intent(intent_id)
        
        intent_data = intent_result.get("data", intent_result)
        status = intent_data.get("status") or intent_result.get("status")
        
        if status not in ["COMPLETED", "SUCCEEDED", "confirmed", "completed"]:
            return jsonify({
                "error": f"Payment not completed. Status: {status}",
                "status": status
            }), 400
        
        amount = existing["amount"]
        
        # Credit wallet
        success, new_balance = WalletFallbackService.credit_wallet(
            user_id=user_id,
            amount=amount,
            source="finternet_topup",
            reference_id=intent_id,
            notes=f"Finternet payment - Intent: {intent_id}"
        )
        
        if not success:
            return jsonify({"error": "Failed to credit wallet"}), 500
        
        # Update pending deposit status
        mongo.pending_wallet_deposits.update_one(
            {"_id": existing["_id"]},
            {"$set": {"status": "completed", "completed_at": datetime.utcnow()}}
        )
        
        # Send notification
        NotificationService.notify_payment_confirmed(
            user_id=user_id,
            amount=amount,
            purpose="Wallet top-up via Finternet"
        )
        
        return jsonify({
            "status": "ok",
            "message": f"Wallet credited with ${amount:.2f}",
            "amount": amount,
            "new_balance": new_balance
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to confirm deposit: {str(e)}"}), 500


@bp.route("/withdraw", methods=["POST"])
@jwt_required()
def withdraw():
    """
    Withdraw from wallet with 1% donation fee via Finternet gateway.
    
    Request body:
    {
        "amount": 50.00
    }
    
    Note: 1% of the withdrawal amount goes to Cooper as a donation.
    For example, withdrawing $100 means you receive $99 and $1 goes to Cooper.
    
    The wallet is debited IMMEDIATELY before redirecting to payment gateway.
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    amount = data.get("amount")
    if not amount or float(amount) <= 0:
        return jsonify({"error": "Valid amount required"}), 400
    
    amount = float(amount)
    
    # Calculate fee (1% donation to Cooper)
    fee = round(amount * WITHDRAWAL_FEE_PERCENT, 2)
    net_amount = round(amount - fee, 2)
    
    # Check if user has enough balance for total withdrawal
    current_balance = WalletFallbackService.get_wallet_balance(user_id)
    if current_balance < amount:
        return jsonify({
            "error": f"Insufficient balance. Available: ${current_balance:.2f}, Requested: ${amount:.2f}"
        }), 400
    
    # Debit the full amount from user IMMEDIATELY (before gateway redirect)
    success, error, amount_debited = WalletFallbackService.debit_wallet(
        user_id=user_id,
        amount=amount,
        purpose="withdrawal",
        notes=f"Wallet withdrawal: ${net_amount:.2f} to user, ${fee:.2f} donation to Cooper"
    )
    
    if not success:
        return jsonify({"error": error}), 400
    
    # Record the fee/donation
    mongo.company_donations.insert_one({
        "user_id": ObjectId(user_id),
        "type": "withdrawal_fee",
        "gross_amount": amount,
        "fee_amount": fee,
        "fee_percent": WITHDRAWAL_FEE_PERCENT * 100,
        "net_to_user": net_amount,
        "created_at": datetime.utcnow()
    })
    
    new_balance = WalletFallbackService.get_wallet_balance(user_id)
    
    # Create Finternet payment intent for the withdrawal (for show/records)
    try:
        finternet = FinternetService()
        intent_response = finternet.create_payment_intent(
            amount=net_amount,
            currency="USD",
            description=f"Cooper wallet withdrawal (net after 1% fee)",
            metadata={
                "type": "wallet_withdrawal",
                "user_id": user_id,
                "gross_amount": str(amount),
                "fee_amount": str(fee),
                "net_amount": str(net_amount)
            }
        )
        payment_url = intent_response.get("payment_url", "")
    except Exception as e:
        # Gateway failed but wallet is already debited - just return success
        payment_url = ""
    
    return jsonify({
        "status": "ok",
        "message": f"${net_amount:.2f} withdrawn (${fee:.2f} donation to Cooper)",
        "gross_amount": amount,
        "fee_amount": fee,
        "fee_percent": WITHDRAWAL_FEE_PERCENT * 100,
        "net_amount": net_amount,
        "amount_withdrawn": net_amount,
        "new_balance": new_balance,
        "payment_url": payment_url
    })


@bp.route("/withdrawal-fee", methods=["GET"])
def get_withdrawal_fee():
    """Get the current withdrawal fee percentage."""
    return jsonify({
        "fee_percent": WITHDRAWAL_FEE_PERCENT * 100,
        "description": "1% of withdrawals go to Cooper as a donation to support the platform"
    })


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

