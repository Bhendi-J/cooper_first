"""
Approval Service - Expense approval workflow.

Responsibilities:
- Handle approval-based expense processing
- Mark expenses as pending until approved
- Don't deduct funds until approved
- Maintain audit trail of approvals
"""
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from bson import ObjectId

from app.extensions import db as mongo


class ApprovalStatus:
    """Approval status constants."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


class ApprovalService:
    """Service for approval-based expense handling."""
    
    @classmethod
    def submit_expense_for_approval(
        cls,
        expense: Dict,
        event_id: str,
        requires_approval: bool,
        trigger_reason: Optional[str] = None
    ) -> Tuple[Dict, bool]:
        """
        Submit an expense, potentially requiring approval.
        
        Args:
            expense: Expense document to submit
            event_id: Event ID
            requires_approval: Whether this expense needs approval
            trigger_reason: Why approval was triggered
            
        Returns:
            Tuple of (expense with status, was_auto_approved)
        """
        from .pool_service import PoolService
        from .notification_service import NotificationService
        
        if requires_approval:
            # Create pending expense
            expense["approval_status"] = ApprovalStatus.PENDING
            expense["status"] = "pending_approval"
            expense["approval_trigger"] = trigger_reason
            
            # Insert expense without deducting from pool
            result = mongo.expenses.insert_one(expense)
            expense["_id"] = str(result.inserted_id)
            
            # Create approval request record
            approval_request = {
                "expense_id": result.inserted_id,
                "event_id": ObjectId(event_id),
                "requested_by": expense["payer_id"],
                "amount": expense["amount"],
                "status": ApprovalStatus.PENDING,
                "trigger_reason": trigger_reason,
                "created_at": datetime.utcnow()
            }
            mongo.approval_requests.insert_one(approval_request)
            
            # Notify creator
            event = mongo.events.find_one({"_id": ObjectId(event_id)})
            if event:
                NotificationService.notify_expense_pending_approval(
                    creator_id=str(event["creator_id"]),
                    event_id=event_id,
                    event_name=event["name"],
                    expense_id=str(result.inserted_id),
                    amount=expense["amount"],
                    reason=trigger_reason
                )
            
            return expense, False
        
        else:
            # Auto-approve and process
            expense["approval_status"] = ApprovalStatus.AUTO_APPROVED
            expense["status"] = "verified"
            expense["approved_at"] = datetime.utcnow()
            
            # Insert expense
            result = mongo.expenses.insert_one(expense)
            expense["_id"] = str(result.inserted_id)
            
            # Deduct from pool
            success, error = PoolService.deduct_expense(
                event_id=event_id,
                expense_id=str(result.inserted_id),
                total_amount=expense["amount"],
                splits=expense["splits"]
            )
            
            if not success:
                # Rollback expense status
                mongo.expenses.update_one(
                    {"_id": result.inserted_id},
                    {"$set": {"status": "failed", "error": error}}
                )
            
            # Create approval record for audit
            mongo.approval_requests.insert_one({
                "expense_id": result.inserted_id,
                "event_id": ObjectId(event_id),
                "requested_by": expense["payer_id"],
                "amount": expense["amount"],
                "status": ApprovalStatus.AUTO_APPROVED,
                "auto_approved_reason": "Under auto-approve threshold",
                "created_at": datetime.utcnow(),
                "approved_at": datetime.utcnow()
            })
            
            return expense, True
    
    @classmethod
    def approve_expense(
        cls,
        expense_id: str,
        approver_id: str,
        notes: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Approve a pending expense.
        
        Deducts funds from pool and individual shares.
        
        Args:
            expense_id: Expense to approve
            approver_id: User approving (must be creator)
            notes: Optional approval notes
            
        Returns:
            Tuple of (success, error_message)
        """
        from .pool_service import PoolService
        from .notification_service import NotificationService
        from .wallet_service import WalletFallbackService
        
        # Get expense
        expense = mongo.expenses.find_one({"_id": ObjectId(expense_id)})
        if not expense:
            return False, "Expense not found"
        
        if expense.get("approval_status") != ApprovalStatus.PENDING:
            return False, f"Expense is not pending approval (status: {expense.get('approval_status')})"
        
        event_id = str(expense["event_id"])
        
        # Verify approver is creator
        event = mongo.events.find_one({"_id": expense["event_id"]})
        if not event:
            return False, "Event not found"
        
        if str(event["creator_id"]) != approver_id:
            return False, "Only the event creator can approve expenses"
        
        # Check pool availability
        is_valid, error = PoolService.validate_pool_operation(
            event_id, expense["amount"]
        )
        
        if not is_valid:
            return False, error
        
        # Process splits with wallet fallback if needed
        splits = expense.get("splits", [])
        processed_splits = []
        debts_created = []
        
        for split in splits:
            user_id = split["user_id"]
            amount = float(split["amount"])
            
            # Check user's contribution
            has_sufficient, available, shortfall = PoolService.check_user_contribution(
                event_id, user_id, amount
            )
            
            if not has_sufficient:
                # Try wallet fallback
                rules = event.get("rules", {})
                if rules.get("allow_wallet_fallback", True):
                    success, debt_info = WalletFallbackService.handle_shortfall(
                        user_id=user_id,
                        event_id=event_id,
                        expense_id=expense_id,
                        required_amount=amount,
                        available_contribution=available
                    )
                    
                    if debt_info:
                        debts_created.append(debt_info)
            
            processed_splits.append(split)
        
        # Deduct from pool
        success, error = PoolService.deduct_expense(
            event_id=event_id,
            expense_id=expense_id,
            total_amount=expense["amount"],
            splits=processed_splits
        )
        
        if not success:
            return False, error
        
        # Update expense status
        mongo.expenses.update_one(
            {"_id": ObjectId(expense_id)},
            {
                "$set": {
                    "approval_status": ApprovalStatus.APPROVED,
                    "status": "verified",
                    "approved_by": ObjectId(approver_id),
                    "approved_at": datetime.utcnow(),
                    "approval_notes": notes,
                    "debts_created": debts_created,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update approval request
        mongo.approval_requests.update_one(
            {"expense_id": ObjectId(expense_id)},
            {
                "$set": {
                    "status": ApprovalStatus.APPROVED,
                    "approved_by": ObjectId(approver_id),
                    "approved_at": datetime.utcnow(),
                    "notes": notes
                }
            }
        )
        
        # Record audit trail
        mongo.approval_audit.insert_one({
            "expense_id": ObjectId(expense_id),
            "event_id": ObjectId(event_id),
            "action": "approved",
            "by_user_id": ObjectId(approver_id),
            "notes": notes,
            "debts_created": debts_created,
            "created_at": datetime.utcnow()
        })
        
        # Notify payer
        NotificationService.notify_expense_approved(
            user_id=str(expense["payer_id"]),
            expense_id=expense_id,
            amount=expense["amount"],
            event_name=event["name"]
        )
        
        return True, None
    
    @classmethod
    def reject_expense(
        cls,
        expense_id: str,
        rejector_id: str,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Reject a pending expense.
        
        No funds are deducted.
        
        Args:
            expense_id: Expense to reject
            rejector_id: User rejecting (must be creator)
            reason: Rejection reason
            
        Returns:
            Tuple of (success, error_message)
        """
        from .notification_service import NotificationService
        
        # Get expense
        expense = mongo.expenses.find_one({"_id": ObjectId(expense_id)})
        if not expense:
            return False, "Expense not found"
        
        if expense.get("approval_status") != ApprovalStatus.PENDING:
            return False, f"Expense is not pending approval"
        
        # Verify rejector is creator
        event = mongo.events.find_one({"_id": expense["event_id"]})
        if not event:
            return False, "Event not found"
        
        if str(event["creator_id"]) != rejector_id:
            return False, "Only the event creator can reject expenses"
        
        # Update expense status
        mongo.expenses.update_one(
            {"_id": ObjectId(expense_id)},
            {
                "$set": {
                    "approval_status": ApprovalStatus.REJECTED,
                    "status": "rejected",
                    "rejected_by": ObjectId(rejector_id),
                    "rejected_at": datetime.utcnow(),
                    "rejection_reason": reason,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update approval request
        mongo.approval_requests.update_one(
            {"expense_id": ObjectId(expense_id)},
            {
                "$set": {
                    "status": ApprovalStatus.REJECTED,
                    "rejected_by": ObjectId(rejector_id),
                    "rejected_at": datetime.utcnow(),
                    "rejection_reason": reason
                }
            }
        )
        
        # Record audit trail
        mongo.approval_audit.insert_one({
            "expense_id": ObjectId(expense_id),
            "event_id": expense["event_id"],
            "action": "rejected",
            "by_user_id": ObjectId(rejector_id),
            "reason": reason,
            "created_at": datetime.utcnow()
        })
        
        # Notify payer
        NotificationService.notify_expense_rejected(
            user_id=str(expense["payer_id"]),
            expense_id=expense_id,
            amount=expense["amount"],
            event_name=event["name"],
            reason=reason
        )
        
        return True, None
    
    @classmethod
    def get_pending_approvals(cls, event_id: str) -> List[Dict]:
        """Get all pending expense approvals for an event."""
        expenses = list(mongo.expenses.find({
            "event_id": ObjectId(event_id),
            "approval_status": ApprovalStatus.PENDING
        }).sort("created_at", 1))
        
        for exp in expenses:
            exp["_id"] = str(exp["_id"])
            exp["event_id"] = str(exp["event_id"])
            exp["payer_id"] = str(exp["payer_id"])
            
            # Get payer info
            payer = mongo.users.find_one({"_id": ObjectId(exp["payer_id"])})
            if payer:
                exp["payer_name"] = payer.get("name", "Unknown")
        
        return expenses
    
    @classmethod
    def get_approval_history(cls, expense_id: str) -> List[Dict]:
        """Get approval audit trail for an expense."""
        history = list(mongo.approval_audit.find({
            "expense_id": ObjectId(expense_id)
        }).sort("created_at", 1))
        
        for h in history:
            h["_id"] = str(h["_id"])
            h["expense_id"] = str(h["expense_id"])
            h["event_id"] = str(h["event_id"])
            h["by_user_id"] = str(h["by_user_id"])
            
            # Get user info
            user = mongo.users.find_one({"_id": ObjectId(h["by_user_id"])})
            if user:
                h["by_user_name"] = user.get("name", "Unknown")
        
        return history
    
    @classmethod
    def cancel_expense(
        cls,
        expense_id: str,
        canceller_id: str,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Cancel an expense (revert if already approved).
        
        Args:
            expense_id: Expense to cancel
            canceller_id: User cancelling (must be creator or payer)
            reason: Cancellation reason
            
        Returns:
            Tuple of (success, error_message)
        """
        from .pool_service import PoolService
        
        expense = mongo.expenses.find_one({"_id": ObjectId(expense_id)})
        if not expense:
            return False, "Expense not found"
        
        event = mongo.events.find_one({"_id": expense["event_id"]})
        if not event:
            return False, "Event not found"
        
        # Check permission - creator or payer
        is_creator = str(event["creator_id"]) == canceller_id
        is_payer = str(expense["payer_id"]) == canceller_id
        
        if not (is_creator or is_payer):
            return False, "Only the event creator or expense payer can cancel"
        
        # If already approved/deducted, revert
        if expense.get("approval_status") in [ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED]:
            success, error = PoolService.revert_expense(
                event_id=str(expense["event_id"]),
                expense_id=expense_id,
                total_amount=expense["amount"],
                splits=expense["splits"]
            )
            
            if not success:
                return False, f"Failed to revert: {error}"
        
        # Update expense status
        mongo.expenses.update_one(
            {"_id": ObjectId(expense_id)},
            {
                "$set": {
                    "status": "cancelled",
                    "approval_status": "cancelled",
                    "cancelled_by": ObjectId(canceller_id),
                    "cancelled_at": datetime.utcnow(),
                    "cancellation_reason": reason,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Record audit
        mongo.approval_audit.insert_one({
            "expense_id": ObjectId(expense_id),
            "event_id": expense["event_id"],
            "action": "cancelled",
            "by_user_id": ObjectId(canceller_id),
            "reason": reason,
            "was_approved": expense.get("approval_status") in [ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED],
            "created_at": datetime.utcnow()
        })
        
        return True, None
