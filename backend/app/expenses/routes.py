# app/expenses/routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime

from app.extensions import db as mongo
from app.utils.merkle_tree import EventMerkleTree
from app.payments.services.finternet import FinternetService
from app.core import (
    ApprovalService, RuleEnforcementService, ExpenseDistributionService,
    PoolService, WalletFallbackService, NotificationService, ReliabilityService
)

expenses_bp = Blueprint("expenses", __name__)

@expenses_bp.route("/", methods=["POST"])
@jwt_required()
def add_expense():
    """
    Add an expense with rule validation, approval workflow, and pool deduction.
    
    Request body:
    {
        "event_id": "...",
        "amount": 100.00,
        "description": "Dinner",
        "category_id": "...",  // optional
        "split_type": "equal|weighted|percentage|exact",  // default: equal
        "split_details": {...}  // required for non-equal splits
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    event_id = str(data["event_id"])
    amount = float(data["amount"])
    description = data.get("description", "")
    category_id = data.get("category_id")
    split_type = data.get("split_type", "equal")
    split_details = data.get("split_details", {})
    selected_members = data.get("selected_members")  # Optional: list of user IDs for custom splits

    # Get event
    event = mongo.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Check if user is authorized participant
    participant = mongo.participants.find_one({
        "event_id": ObjectId(event_id),
        "user_id": ObjectId(user_id),
        "status": "active"
    })
    if not participant:
        return jsonify({"error": "Not an active participant"}), 403

    # Get all active participants
    all_participants = list(
        mongo.participants.find(
            {"event_id": ObjectId(event_id), "status": "active"}
        )
    )

    if not all_participants:
        return jsonify({"error": "No active participants"}), 400

    # Filter participants if selected_members is provided
    if selected_members and len(selected_members) > 0:
        participants = [p for p in all_participants if str(p["user_id"]) in selected_members]
        if not participants:
            return jsonify({"error": "No valid participants selected"}), 400
    else:
        participants = all_participants

    # Validate against event rules
    # Returns: (is_valid, error_message, violation_type, requires_approval)
    is_valid, error_message, violation_type, rule_requires_approval = RuleEnforcementService.validate_expense(
        event_id=event_id,
        payer_id=user_id,
        amount=amount,
        category_id=category_id
    )
    
    if not is_valid:
        # Log the violation
        RuleEnforcementService.record_rule_violation(
            event_id=event_id,
            user_id=user_id,
            violation_type=violation_type or "unknown",
            details=error_message or "Rule violation"
        )
        
        # Notify about violation
        NotificationService.notify_rule_violation(
            user_id=user_id,
            event_id=event_id,
            event_name=event.get("name", "Event"),
            violation_type="expense_rule",
            details=error_message or "Rule violation"
        )
        
        return jsonify({
            "error": "Expense violates event rules",
            "violations": [{"type": violation_type, "message": error_message}]
        }), 400

    # Calculate splits based on split type
    participant_ids = [str(p["user_id"]) for p in participants]
    
    if split_type == "equal":
        split_amounts = ExpenseDistributionService.calculate_equal_split(
            amount, participant_ids
        )
    elif split_type == "weighted":
        weights = split_details.get("weights", {})
        split_amounts = ExpenseDistributionService.calculate_weighted_split(
            amount, weights
        )
    elif split_type == "percentage":
        percentages = split_details.get("percentages", {})
        split_amounts, split_error = ExpenseDistributionService.calculate_percentage_split(
            amount, percentages
        )
        if split_error:
            return jsonify({"error": split_error}), 400
    elif split_type == "exact":
        exact_amounts = split_details.get("amounts", {})
        split_amounts, split_error = ExpenseDistributionService.calculate_exact_split(
            amount, exact_amounts
        )
        if split_error:
            return jsonify({"error": split_error}), 400
    else:
        split_amounts = ExpenseDistributionService.calculate_equal_split(
            amount, participant_ids
        )

    # Build splits array - split_amounts is a list of dicts from ExpenseDistributionService
    # Convert to lookup dict for easier access
    split_amounts_dict = {s["user_id"]: s["amount"] for s in split_amounts}
    
    splits = []
    for p in participants:
        pid = str(p["user_id"])
        splits.append({
            "user_id": pid,
            "amount": float(split_amounts_dict.get(pid, 0)),
            "status": "pending"
        })

    # Validate splits
    is_valid, validation_error = ExpenseDistributionService.validate_splits(event_id, amount, splits)
    if not is_valid:
        return jsonify({
            "error": "Invalid split configuration",
            "details": validation_error
        }), 400

    # Check if approval is required
    rules = event.get("rules", {})
    auto_approve_under = rules.get("auto_approve_under", 100)
    approval_required = rules.get("approval_required", False) or rule_requires_approval
    
    # Check reliability-based forced approval
    adjusted_rules = ReliabilityService.apply_reliability_adjustments(
        user_id, event_id, rules
    )
    if adjusted_rules.get("approval_required"):
        approval_required = True
    
    needs_approval = approval_required or amount >= auto_approve_under

    # Create the expense record
    expense = {
        "event_id": ObjectId(event_id),
        "payer_id": ObjectId(user_id),
        "amount": amount,
        "description": description,
        "category_id": ObjectId(category_id) if category_id else None,
        "split_type": split_type,
        "splits": splits,
        "status": "pending_approval" if needs_approval else "pending",
        "approval_status": "pending" if needs_approval else None,
        "created_at": datetime.utcnow()
    }

    if needs_approval:
        # Submit for approval - ApprovalService will insert the expense
        expense_doc, was_auto_approved = ApprovalService.submit_expense_for_approval(
            expense=expense,
            event_id=event_id,
            requires_approval=True,
            trigger_reason="Amount exceeds auto-approve threshold" if amount >= auto_approve_under else "Approval required by reliability tier"
        )
        expense_id = expense_doc.get("_id") or str(expense_doc.get("_id"))
        
        # Notify creator
        NotificationService.notify_expense_pending_approval(
            creator_id=str(event["creator_id"]),
            event_id=event_id,
            event_name=event.get("name", "Event"),
            expense_id=expense_id,
            amount=amount,
            reason="Amount exceeds auto-approve threshold" if amount >= auto_approve_under else "Approval required by reliability tier"
        )
        
        # Prepare response
        expense_doc["event_id"] = event_id
        expense_doc["payer_id"] = user_id
        if expense_doc.get("category_id"):
            expense_doc["category_id"] = str(expense_doc["category_id"])
        if hasattr(expense_doc.get("created_at"), 'isoformat'):
            expense_doc["created_at"] = expense_doc["created_at"].isoformat()
        
        return jsonify({
            "expense": expense_doc,
            "status": "pending_approval",
            "message": "Expense submitted for approval"
        }), 202

    # Auto-approved expense - insert and process pool deduction
    result = mongo.expenses.insert_one(expense)
    expense_id = str(result.inserted_id)
    
    # Deduct from pool with correct parameters
    pool_success, pool_error = PoolService.deduct_expense(
        event_id=event_id,
        expense_id=expense_id,
        total_amount=amount,
        splits=splits
    )
    
    shortfall_debts = []
    if not pool_success and "Insufficient" in pool_error:
        # Handle shortfall with wallet fallback
        for split in splits:
            split_user_id = split["user_id"]
            split_amount = split["amount"]
            
            fallback_result = WalletFallbackService.handle_shortfall(
                user_id=split_user_id,
                event_id=event_id,
                amount=split_amount
            )
            
            if fallback_result.get("debt_created"):
                shortfall_debts.append({
                    "user_id": split_user_id,
                    "amount": fallback_result.get("debt_amount"),
                    "debt_id": fallback_result.get("debt_id")
                })
                
                # Notify user about debt
                NotificationService.notify_debt_created(
                    user_id=split_user_id,
                    amount=fallback_result.get("debt_amount"),
                    event_id=event_id,
                    expense_id=expense_id
                )

    # Update expense status
    mongo.expenses.update_one(
        {"_id": result.inserted_id},
        {"$set": {"status": "approved", "approved_at": datetime.utcnow()}}
    )
    
    # Convert ObjectIds to strings for JSON response
    expense["_id"] = expense_id
    expense["event_id"] = event_id
    expense["payer_id"] = user_id
    if expense["category_id"]:
        expense["category_id"] = str(expense["category_id"])
    expense["created_at"] = expense["created_at"].isoformat()

    # 🔐 Merkle Tree Update
    all_expenses = list(mongo.expenses.find({"event_id": ObjectId(event_id)}))
    merkle_tree = EventMerkleTree.build_event_tree(event_id, all_expenses)
    merkle_root = merkle_tree.get_root()

    # Find the index of the newly added expense and get its proof
    expense_index = len(all_expenses) - 1
    merkle_proof = merkle_tree.get_proof(expense_index)

    # Store the merkle proof with the expense
    mongo.expenses.update_one(
        {"_id": result.inserted_id},
        {"$set": {"merkle_proof": merkle_proof}}
    )
    expense["merkle_proof"] = merkle_proof

    # Update proofs for all other expenses since the tree changed
    for i, exp in enumerate(all_expenses[:-1]):
        proof = merkle_tree.get_proof(i)
        mongo.expenses.update_one(
            {"_id": exp["_id"]},
            {"$set": {"merkle_proof": proof}}
        )

    mongo.events.update_one(
        {"_id": ObjectId(event_id)},
        {
            "$set": {"merkle_root": merkle_root},
            "$inc": {"total_spent": amount}
        }
    )

    # Update participant balances
    for p in participants:
        if str(p["user_id"]) == user_id:
            balance_change = amount - split_amounts_dict.get(str(p["user_id"]), 0)
        else:
            balance_change = -split_amounts_dict.get(str(p["user_id"]), 0)

        mongo.participants.update_one(
            {"_id": p["_id"]},
            {
                "$inc": {
                    "balance": balance_change,
                    "total_spent": split_amounts_dict.get(str(p["user_id"]), 0)
                }
            }
        )

    # Log expense activity
    mongo.activities.insert_one({
        "type": "expense",
        "event_id": ObjectId(event_id),
        "user_id": ObjectId(user_id),
        "amount": amount,
        "description": description or "Expense",
        "expense_id": result.inserted_id,
        "created_at": datetime.utcnow()
    })

    return jsonify({
        "expense": expense,
        "merkle_root": merkle_root,
        "shortfall_debts": shortfall_debts if shortfall_debts else None
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


# ------------------ EXPENSE APPROVAL ENDPOINTS ------------------

@expenses_bp.route("/pending-approvals/<event_id>", methods=["GET"])
@jwt_required()
def get_pending_approvals(event_id):
    """Get expenses pending approval for an event (creator only)."""
    user_id = get_jwt_identity()
    
    event = mongo.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    if str(event["creator_id"]) != user_id:
        return jsonify({"error": "Only creator can view pending approvals"}), 403
    
    pending = ApprovalService.get_pending_approvals(event_id)
    
    return jsonify({"pending_approvals": pending})


@expenses_bp.route("/<expense_id>/approve", methods=["POST"])
@jwt_required()
def approve_expense(expense_id):
    """Approve an expense (creator only)."""
    user_id = get_jwt_identity()
    
    expense = mongo.expenses.find_one({"_id": ObjectId(expense_id)})
    if not expense:
        return jsonify({"error": "Expense not found"}), 404
    
    event = mongo.events.find_one({"_id": expense["event_id"]})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    if str(event["creator_id"]) != user_id:
        return jsonify({"error": "Only creator can approve expenses"}), 403
    
    # Approve the expense
    result = ApprovalService.approve_expense(
        expense_id=expense_id,
        approved_by=user_id
    )
    
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400
    
    event_id = str(expense["event_id"])
    amount = expense["amount"]
    
    # Now deduct from pool
    pool_result = PoolService.deduct_expense(event_id, amount, expense_id)
    
    shortfall_debts = []
    if pool_result.get("shortfall", 0) > 0:
        # Handle shortfall with wallet fallback
        for split in expense.get("splits", []):
            split_user_id = split["user_id"]
            split_amount = split["amount"]
            
            fallback_result = WalletFallbackService.handle_shortfall(
                user_id=split_user_id,
                event_id=event_id,
                amount=split_amount
            )
            
            if fallback_result.get("debt_created"):
                shortfall_debts.append({
                    "user_id": split_user_id,
                    "amount": fallback_result.get("debt_amount"),
                    "debt_id": fallback_result.get("debt_id")
                })
                
                NotificationService.notify_debt_created(
                    user_id=split_user_id,
                    amount=fallback_result.get("debt_amount"),
                    event_id=event_id,
                    expense_id=expense_id
                )
    
    # Update expense status
    mongo.expenses.update_one(
        {"_id": ObjectId(expense_id)},
        {"$set": {
            "status": "approved",
            "approval_status": "approved",
            "approved_at": datetime.utcnow(),
            "approved_by": ObjectId(user_id)
        }}
    )
    
    # Update event totals
    mongo.events.update_one(
        {"_id": expense["event_id"]},
        {"$inc": {"total_spent": amount}}
    )
    
    # Notify the expense creator
    NotificationService.notify_expense_approved(
        user_id=str(expense["payer_id"]),
        expense_id=expense_id,
        amount=amount,
        event_name=event.get("name", "Event")
    )
    
    return jsonify({
        "message": "Expense approved",
        "expense_id": expense_id,
        "shortfall_debts": shortfall_debts if shortfall_debts else None
    })


@expenses_bp.route("/<expense_id>/reject", methods=["POST"])
@jwt_required()
def reject_expense(expense_id):
    """Reject an expense (creator only)."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    expense = mongo.expenses.find_one({"_id": ObjectId(expense_id)})
    if not expense:
        return jsonify({"error": "Expense not found"}), 404
    
    event = mongo.events.find_one({"_id": expense["event_id"]})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    if str(event["creator_id"]) != user_id:
        return jsonify({"error": "Only creator can reject expenses"}), 403
    
    reason = data.get("reason", "")
    
    # Reject the expense
    result = ApprovalService.reject_expense(
        expense_id=expense_id,
        rejected_by=user_id,
        reason=reason
    )
    
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400
    
    # Update expense status
    mongo.expenses.update_one(
        {"_id": ObjectId(expense_id)},
        {"$set": {
            "status": "rejected",
            "approval_status": "rejected",
            "rejected_at": datetime.utcnow(),
            "rejected_by": ObjectId(user_id),
            "rejection_reason": reason
        }}
    )
    
    # Notify the expense creator
    NotificationService.notify_expense_rejected(
        user_id=str(expense["payer_id"]),
        expense_id=expense_id,
        amount=expense["amount"],
        event_name=event.get("name", "Event"),
        reason=reason
    )
    
    return jsonify({
        "message": "Expense rejected",
        "expense_id": expense_id
    })


@expenses_bp.route("/<expense_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_expense(expense_id):
    """Cancel a pending expense (expense creator only)."""
    user_id = get_jwt_identity()
    
    expense = mongo.expenses.find_one({"_id": ObjectId(expense_id)})
    if not expense:
        return jsonify({"error": "Expense not found"}), 404
    
    if str(expense["payer_id"]) != user_id:
        return jsonify({"error": "Only expense creator can cancel"}), 403
    
    if expense.get("status") not in ["pending", "pending_approval"]:
        return jsonify({"error": "Can only cancel pending expenses"}), 400
    
    # Cancel the expense
    result = ApprovalService.cancel_expense(expense_id, user_id)
    
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400
    
    # Update expense status
    mongo.expenses.update_one(
        {"_id": ObjectId(expense_id)},
        {"$set": {
            "status": "cancelled",
            "cancelled_at": datetime.utcnow()
        }}
    )
    
    return jsonify({
        "message": "Expense cancelled",
        "expense_id": expense_id
    })


@expenses_bp.route("/pay", methods=["POST"])
@jwt_required()
def create_expense_with_payment():
    """
    Create an expense and initiate payment via Finternet gateway.
    
    This endpoint creates the expense record and returns a payment URL
    for the user to complete the payment. Once payment is confirmed,
    the expense will be processed.
    
    Request body:
    {
        "event_id": "...",
        "amount": 100.00,
        "description": "Dinner",
        "category_id": "...",  // optional
        "split_type": "equal|weighted|percentage|exact",
        "split_details": {...},
        "selected_members": [...]  // optional
    }
    """
    from app.payments.services.finternet import FinternetService
    
    user_id = get_jwt_identity()
    data = request.get_json()

    event_id = str(data["event_id"])
    amount = float(data["amount"])
    description = data.get("description", "")

    # Get event
    event = mongo.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Check if user is authorized participant
    participant = mongo.participants.find_one({
        "event_id": ObjectId(event_id),
        "user_id": ObjectId(user_id),
        "status": "active"
    })
    if not participant:
        return jsonify({"error": "Not an active participant"}), 403

    try:
        # Create payment intent via Finternet (using DELIVERY_VS_PAYMENT type per Postman collection)
        finternet = FinternetService()
        result = finternet.create_payment_intent(
            amount=str(amount),
            currency="USD",  # Use USD as per Postman collection
            payment_type="DELIVERY_VS_PAYMENT",
            settlement_method="OFF_RAMP_MOCK",
            settlement_destination="bank_account_123",
            description=description or f"Expense for {event.get('name', 'Event')}"
        )
        
        intent_data = result.get("data", result)
        intent_id = intent_data.get("id")
        
        # Construct payment URL - redirect to Finternet payment page
        payment_url = (
            intent_data.get("paymentUrl") or 
            intent_data.get("payment_url") or 
            f"https://pay.fmm.finternetlab.io/?intent={intent_id}"
        )
        
        # Store pending expense with payment intent
        pending_expense = {
            "event_id": ObjectId(event_id),
            "payer_id": ObjectId(user_id),
            "amount": amount,
            "description": description,
            "category_id": ObjectId(data.get("category_id")) if data.get("category_id") else None,
            "split_type": data.get("split_type", "equal"),
            "split_details": data.get("split_details", {}),
            "selected_members": data.get("selected_members"),
            "payment_intent_id": intent_id,
            "payment_status": "pending",
            "status": "awaiting_payment",
            "created_at": datetime.utcnow()
        }
        
        result = mongo.pending_expenses.insert_one(pending_expense)
        
        return jsonify({
            "pending_expense_id": str(result.inserted_id),
            "payment_intent_id": intent_id,
            "payment_url": payment_url,
            "amount": amount,
            "message": "Complete payment to finalize the expense"
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to create payment: {str(e)}"}), 500


@expenses_bp.route("/pay/<pending_id>/confirm", methods=["POST"])
@jwt_required()
def confirm_expense_payment(pending_id):
    """
    Confirm that payment was completed and process the expense.
    Called after the payment gateway confirms the transaction.
    """
    user_id = get_jwt_identity()
    
    # Get pending expense
    pending = mongo.pending_expenses.find_one({"_id": ObjectId(pending_id)})
    if not pending:
        return jsonify({"error": "Pending expense not found"}), 404
    
    if str(pending["payer_id"]) != user_id:
        return jsonify({"error": "Not authorized"}), 403
    
    if pending.get("payment_status") == "completed":
        return jsonify({"error": "Payment already confirmed"}), 400
    
    # Verify payment with Finternet
    from app.payments.services.finternet import FinternetService
    try:
        finternet = FinternetService()
        intent_status = finternet.get_payment_intent(pending["payment_intent_id"])
        intent_data = intent_status.get("data", intent_status)
        
        status = intent_data.get("status", "").upper()
        if status not in ["SUCCEEDED", "SETTLED", "FINAL"]:
            return jsonify({
                "error": "Payment not yet completed",
                "payment_status": status
            }), 400
            
    except Exception as e:
        return jsonify({"error": f"Failed to verify payment: {str(e)}"}), 500
    
    # Payment confirmed - create the actual expense
    event_id = str(pending["event_id"])
    amount = pending["amount"]
    
    # Build splits (simplified - uses the logic from add_expense)
    event = mongo.events.find_one({"_id": pending["event_id"]})
    participants = list(mongo.participants.find({
        "event_id": pending["event_id"],
        "status": "active"
    }))
    
    participant_ids = [str(p["user_id"]) for p in participants]
    split_amounts = ExpenseDistributionService.calculate_equal_split(amount, participant_ids)
    split_amounts_dict = {s["user_id"]: s["amount"] for s in split_amounts}
    
    splits = []
    for p in participants:
        pid = str(p["user_id"])
        splits.append({
            "user_id": pid,
            "amount": float(split_amounts_dict.get(pid, 0)),
            "status": "paid"  # Payment already made via gateway
        })
    
    # Create expense record
    expense = {
        "event_id": pending["event_id"],
        "payer_id": pending["payer_id"],
        "amount": amount,
        "description": pending.get("description", ""),
        "category_id": pending.get("category_id"),
        "split_type": pending.get("split_type", "equal"),
        "splits": splits,
        "status": "approved",
        "payment_method": "gateway",
        "payment_intent_id": pending["payment_intent_id"],
        "created_at": pending["created_at"],
        "approved_at": datetime.utcnow()
    }
    
    result = mongo.expenses.insert_one(expense)
    expense_id = str(result.inserted_id)
    
    # Update event total spent
    mongo.events.update_one(
        {"_id": pending["event_id"]},
        {"$inc": {"total_spent": amount}}
    )
    
    # Mark pending expense as completed
    mongo.pending_expenses.update_one(
        {"_id": ObjectId(pending_id)},
        {"$set": {
            "payment_status": "completed",
            "expense_id": result.inserted_id,
            "completed_at": datetime.utcnow()
        }}
    )
    
    # Log activity
    mongo.activities.insert_one({
        "type": "expense",
        "event_id": pending["event_id"],
        "user_id": pending["payer_id"],
        "amount": amount,
        "description": pending.get("description") or "Expense (paid via gateway)",
        "expense_id": result.inserted_id,
        "payment_method": "gateway",
        "created_at": datetime.utcnow()
    })
    
    return jsonify({
        "message": "Expense created successfully",
        "expense_id": expense_id,
        "amount": amount
    })