"""
Debt Service - Structured debt tracking and settlement.

Responsibilities:
- Track unpaid amounts with expense references
- Handle debt settlement via payments/refunds
- Apply restrictions for excessive debt
- Handle debt aging and reminders
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from bson import ObjectId

from app.extensions import db as mongo


class DebtStatus:
    """Debt status constants."""
    OUTSTANDING = "outstanding"
    PARTIALLY_PAID = "partially_paid"
    SETTLED = "settled"
    FORGIVEN = "forgiven"


class DebtService:
    """Service for structured debt handling."""
    
    # Debt aging thresholds (in days)
    WARNING_THRESHOLD = 7
    RESTRICTION_THRESHOLD = 14
    CRITICAL_THRESHOLD = 30
    
    @classmethod
    def create_debt(
        cls,
        user_id: str,
        event_id: str,
        expense_id: str,
        amount: float,
        reason: Optional[str] = None
    ) -> Dict:
        """
        Create a new debt record.
        
        Args:
            user_id: User who owes
            event_id: Related event
            expense_id: Related expense
            amount: Amount owed
            reason: Why debt was created
            
        Returns:
            Created debt record
        """
        debt = {
            "user_id": ObjectId(user_id),
            "event_id": ObjectId(event_id),
            "expense_id": ObjectId(expense_id),
            "amount_original": round(float(amount), 2),
            "amount_remaining": round(float(amount), 2),
            "amount_paid": 0.0,
            "status": DebtStatus.OUTSTANDING,
            "reason": reason,
            "payments": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "due_date": datetime.utcnow() + timedelta(days=cls.WARNING_THRESHOLD)
        }
        
        result = mongo.debts.insert_one(debt)
        debt["_id"] = str(result.inserted_id)
        debt["user_id"] = str(debt["user_id"])
        debt["event_id"] = str(debt["event_id"])
        debt["expense_id"] = str(debt["expense_id"])
        
        # Update user's debt metrics
        cls._update_user_debt_metrics(user_id)
        
        return debt
    
    @classmethod
    def settle_debt(
        cls,
        debt_id: str,
        payment_id: str,
        amount: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Apply a payment to a debt.
        
        Args:
            debt_id: Debt to settle
            payment_id: Reference to payment
            amount: Amount being paid
            
        Returns:
            Tuple of (success, error_message)
        """
        debt = mongo.debts.find_one({"_id": ObjectId(debt_id)})
        if not debt:
            return False, "Debt not found"
        
        if debt["status"] == DebtStatus.SETTLED:
            return False, "Debt already settled"
        
        amount = round(float(amount), 2)
        remaining = float(debt["amount_remaining"])
        
        # Calculate new remaining
        new_remaining = max(0, remaining - amount)
        new_paid = float(debt["amount_paid"]) + min(amount, remaining)
        
        # Determine new status
        if new_remaining <= 0.01:
            new_status = DebtStatus.SETTLED
        else:
            new_status = DebtStatus.PARTIALLY_PAID
        
        # Update debt
        mongo.debts.update_one(
            {"_id": ObjectId(debt_id)},
            {
                "$set": {
                    "amount_remaining": round(new_remaining, 2),
                    "amount_paid": round(new_paid, 2),
                    "status": new_status,
                    "updated_at": datetime.utcnow(),
                    "settled_at": datetime.utcnow() if new_status == DebtStatus.SETTLED else None
                },
                "$push": {
                    "payments": {
                        "payment_id": payment_id,
                        "amount": min(amount, remaining),
                        "paid_at": datetime.utcnow()
                    }
                }
            }
        )
        
        # Update user metrics
        cls._update_user_debt_metrics(str(debt["user_id"]))
        
        return True, None
    
    @classmethod
    def forgive_debt(
        cls,
        debt_id: str,
        forgiver_id: str,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Forgive a debt (creator only).
        
        Args:
            debt_id: Debt to forgive
            forgiver_id: User forgiving (must be event creator)
            reason: Reason for forgiveness
            
        Returns:
            Tuple of (success, error_message)
        """
        debt = mongo.debts.find_one({"_id": ObjectId(debt_id)})
        if not debt:
            return False, "Debt not found"
        
        # Verify forgiver is event creator
        event = mongo.events.find_one({"_id": debt["event_id"]})
        if not event or str(event["creator_id"]) != forgiver_id:
            return False, "Only the event creator can forgive debts"
        
        mongo.debts.update_one(
            {"_id": ObjectId(debt_id)},
            {
                "$set": {
                    "status": DebtStatus.FORGIVEN,
                    "forgiven_by": ObjectId(forgiver_id),
                    "forgiven_at": datetime.utcnow(),
                    "forgiveness_reason": reason,
                    "amount_remaining": 0,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update user metrics
        cls._update_user_debt_metrics(str(debt["user_id"]))
        
        return True, None
    
    @classmethod
    def get_user_debts(
        cls,
        user_id: str,
        event_id: Optional[str] = None,
        include_settled: bool = False
    ) -> List[Dict]:
        """Get all debts for a user."""
        query = {"user_id": ObjectId(user_id)}
        
        if event_id:
            query["event_id"] = ObjectId(event_id)
        
        if not include_settled:
            query["status"] = {"$in": [DebtStatus.OUTSTANDING, DebtStatus.PARTIALLY_PAID]}
        
        debts = list(mongo.debts.find(query).sort("created_at", -1))
        
        for d in debts:
            d["_id"] = str(d["_id"])
            d["user_id"] = str(d["user_id"])
            d["event_id"] = str(d["event_id"])
            d["expense_id"] = str(d["expense_id"])
            
            # Calculate age
            d["age_days"] = (datetime.utcnow() - d["created_at"]).days
            d["is_overdue"] = d["age_days"] > cls.WARNING_THRESHOLD
        
        return debts
    
    @classmethod
    def get_user_outstanding_debts(cls, user_id: str) -> List[Dict]:
        """Get only outstanding debts for a user."""
        return cls.get_user_debts(user_id, include_settled=False)
    
    @classmethod
    def get_total_outstanding(cls, user_id: str) -> float:
        """Get total outstanding debt for a user."""
        debts = cls.get_user_outstanding_debts(user_id)
        return sum(float(d["amount_remaining"]) for d in debts)
    
    @classmethod
    def check_debt_restrictions(
        cls,
        user_id: str,
        event_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user has debt-based restrictions.
        
        Args:
            user_id: User to check
            event_id: Event context
            
        Returns:
            Tuple of (has_restrictions, restriction_message)
        """
        from .rules_service import RuleEnforcementService
        
        rules = RuleEnforcementService.get_event_rules(event_id)
        max_debt = rules.get("max_debt_allowed")
        
        total_outstanding = cls.get_total_outstanding(user_id)
        
        if max_debt is not None and total_outstanding >= max_debt:
            return True, f"Outstanding debt (${total_outstanding:.2f}) exceeds limit (${max_debt:.2f})"
        
        # Check for critically overdue debts
        debts = cls.get_user_outstanding_debts(user_id)
        critical_debts = [d for d in debts if d.get("age_days", 0) >= cls.CRITICAL_THRESHOLD]
        
        if critical_debts:
            return True, f"You have {len(critical_debts)} critically overdue debt(s)"
        
        return False, None
    
    @classmethod
    def get_event_debts(cls, event_id: str) -> List[Dict]:
        """Get all debts for an event."""
        debts = list(mongo.debts.find({
            "event_id": ObjectId(event_id)
        }).sort("created_at", -1))
        
        for d in debts:
            d["_id"] = str(d["_id"])
            d["user_id"] = str(d["user_id"])
            d["event_id"] = str(d["event_id"])
            d["expense_id"] = str(d["expense_id"])
            
            # Get user info
            user = mongo.users.find_one({"_id": ObjectId(d["user_id"])})
            if user:
                d["user_name"] = user.get("name", "Unknown")
        
        return debts
    
    @classmethod
    def apply_refund_to_debts(
        cls,
        user_id: str,
        event_id: str,
        refund_amount: float,
        refund_id: str
    ) -> Tuple[float, List[Dict]]:
        """
        Apply a refund to outstanding debts in the event.
        
        Args:
            user_id: User receiving refund
            event_id: Event context
            refund_amount: Amount to apply
            refund_id: Reference to refund
            
        Returns:
            Tuple of (remaining_refund, settled_debts)
        """
        debts = cls.get_user_debts(user_id, event_id=event_id, include_settled=False)
        
        remaining = refund_amount
        settled = []
        
        for debt in debts:
            if remaining <= 0:
                break
            
            debt_remaining = float(debt["amount_remaining"])
            settle_amount = min(remaining, debt_remaining)
            
            success, _ = cls.settle_debt(
                debt_id=debt["_id"],
                payment_id=refund_id,
                amount=settle_amount
            )
            
            if success:
                remaining -= settle_amount
                settled.append({
                    "debt_id": debt["_id"],
                    "amount_settled": settle_amount
                })
        
        return remaining, settled
    
    @classmethod
    def _update_user_debt_metrics(cls, user_id: str) -> None:
        """Update user's aggregate debt metrics."""
        debts = cls.get_user_outstanding_debts(user_id)
        
        total_outstanding = sum(float(d["amount_remaining"]) for d in debts)
        count_outstanding = len(debts)
        oldest_debt_age = max((d.get("age_days", 0) for d in debts), default=0)
        
        mongo.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "debt_metrics": {
                        "total_outstanding": round(total_outstanding, 2),
                        "count_outstanding": count_outstanding,
                        "oldest_debt_days": oldest_debt_age,
                        "updated_at": datetime.utcnow()
                    }
                }
            }
        )
    
    @classmethod
    def get_overdue_debts(cls, threshold_days: int = None) -> List[Dict]:
        """Get all overdue debts (for reminder processing)."""
        if threshold_days is None:
            threshold_days = cls.WARNING_THRESHOLD
        
        cutoff = datetime.utcnow() - timedelta(days=threshold_days)
        
        debts = list(mongo.debts.find({
            "status": {"$in": [DebtStatus.OUTSTANDING, DebtStatus.PARTIALLY_PAID]},
            "created_at": {"$lt": cutoff}
        }))
        
        for d in debts:
            d["_id"] = str(d["_id"])
            d["user_id"] = str(d["user_id"])
            d["event_id"] = str(d["event_id"])
            d["expense_id"] = str(d["expense_id"])
            d["age_days"] = (datetime.utcnow() - d["created_at"]).days
        
        return debts
    
    @classmethod
    def handle_participant_leaving(
        cls,
        event_id: str,
        user_id: str
    ) -> Tuple[bool, Optional[str], List[Dict]]:
        """
        Handle when a participant leaves with unsettled debts.
        
        Args:
            event_id: Event ID
            user_id: User leaving
            
        Returns:
            Tuple of (can_leave, error_message, outstanding_debts)
        """
        debts = cls.get_user_debts(user_id, event_id=event_id, include_settled=False)
        
        if debts:
            total = sum(float(d["amount_remaining"]) for d in debts)
            return False, f"Cannot leave with ${total:.2f} in outstanding debts", debts
        
        return True, None, []
