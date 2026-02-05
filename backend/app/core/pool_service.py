"""
Pool Service - Shared pool management.

Responsibilities:
- Handle confirmed deposits and update pool state
- Update user's available contribution
- Validate pool state before operations
- Deduct from pool on approved expenses
"""
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from bson import ObjectId

from app.extensions import db as mongo


class PoolService:
    """Service for managing shared pool operations."""
    
    @classmethod
    def confirm_deposit(
        cls,
        event_id: str,
        user_id: str,
        amount: float,
        payment_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Confirm a deposit after payment verification.
        
        Updates user's available contribution and pool availability.
        
        Args:
            event_id: Event ID
            user_id: User ID
            amount: Deposit amount
            payment_id: Reference to payment record
            
        Returns:
            Tuple of (success, message)
        """
        amount = round(float(amount), 2)
        
        # Get participant
        participant = mongo.participants.find_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id)
        })
        
        if not participant:
            return False, "Participant not found"
        
        # Update participant's deposit and balance
        result = mongo.participants.update_one(
            {"_id": participant["_id"]},
            {
                "$inc": {
                    "deposit_amount": amount,
                    "balance": amount,
                    "available_contribution": amount
                },
                "$set": {"updated_at": datetime.utcnow()},
                "$push": {
                    "deposit_history": {
                        "amount": amount,
                        "payment_id": payment_id,
                        "confirmed_at": datetime.utcnow()
                    }
                }
            }
        )
        
        if result.modified_count == 0:
            return False, "Failed to update participant"
        
        # Update event pool
        mongo.events.update_one(
            {"_id": ObjectId(event_id)},
            {
                "$inc": {"total_pool": amount},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # Record deposit activity
        mongo.activities.insert_one({
            "type": "deposit_confirmed",
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "amount": amount,
            "payment_id": payment_id,
            "description": f"Deposit confirmed: ${amount:.2f}",
            "created_at": datetime.utcnow()
        })
        
        return True, "Deposit confirmed"
    
    @classmethod
    def get_pool_state(cls, event_id: str) -> Dict[str, Any]:
        """
        Get current pool state for an event.
        
        Returns:
            Pool state including total, spent, available, and per-user breakdown
        """
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            return {}
        
        participants = list(mongo.participants.find({
            "event_id": ObjectId(event_id),
            "status": {"$in": ["active", "approved"]}
        }))
        
        total_pool = float(event.get("total_pool", 0))
        total_spent = float(event.get("total_spent", 0))
        available = total_pool - total_spent
        
        user_breakdown = []
        for p in participants:
            user = mongo.users.find_one({"_id": p["user_id"]})
            user_breakdown.append({
                "user_id": str(p["user_id"]),
                "user_name": user.get("name", "Unknown") if user else "Unknown",
                "deposited": round(p.get("deposit_amount", 0), 2),
                "spent": round(p.get("total_spent", 0), 2),
                "balance": round(p.get("balance", 0), 2),
                "available_contribution": round(p.get("available_contribution", p.get("balance", 0)), 2)
            })
        
        return {
            "event_id": event_id,
            "total_pool": round(total_pool, 2),
            "total_spent": round(total_spent, 2),
            "available": round(available, 2),
            "participant_count": len(participants),
            "users": user_breakdown
        }
    
    @classmethod
    def validate_pool_operation(
        cls,
        event_id: str,
        amount: float,
        operation: str = "expense"
    ) -> Tuple[bool, str]:
        """
        Validate that a pool operation won't result in invalid state.
        
        Args:
            event_id: Event ID
            amount: Amount to deduct
            operation: Type of operation (expense, refund, etc.)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        state = cls.get_pool_state(event_id)
        
        if not state:
            return False, "Event not found"
        
        available = state["available"]
        
        if amount > available:
            return False, f"Insufficient pool balance. Available: ${available:.2f}, Required: ${amount:.2f}"
        
        # Additional validation for negative pool
        if available - amount < 0:
            return False, "Operation would result in negative pool balance"
        
        return True, ""
    
    @classmethod
    def deduct_expense(
        cls,
        event_id: str,
        expense_id: str,
        total_amount: float,
        splits: list
    ) -> Tuple[bool, str]:
        """
        Deduct expense from pool and individual shares.
        
        Only called for approved expenses.
        
        Args:
            event_id: Event ID
            expense_id: Expense ID
            total_amount: Total expense amount
            splits: List of {user_id, amount} dicts
            
        Returns:
            Tuple of (success, error_message)
        """
        # Validate pool state
        is_valid, error = cls.validate_pool_operation(event_id, total_amount)
        if not is_valid:
            return False, error
        
        # Start deduction
        try:
            # Update event total spent
            mongo.events.update_one(
                {"_id": ObjectId(event_id)},
                {
                    "$inc": {"total_spent": total_amount},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            # Update individual participant balances
            for split in splits:
                user_id = split["user_id"]
                amount = float(split["amount"])
                
                mongo.participants.update_one(
                    {
                        "event_id": ObjectId(event_id),
                        "user_id": ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id
                    },
                    {
                        "$inc": {
                            "total_spent": amount,
                            "balance": -amount,
                            "available_contribution": -amount
                        },
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
            
            return True, ""
            
        except Exception as e:
            return False, f"Deduction failed: {str(e)}"
    
    @classmethod
    def check_user_contribution(
        cls,
        event_id: str,
        user_id: str,
        required_amount: float
    ) -> Tuple[bool, float, float]:
        """
        Check if user has sufficient contribution for an expense share.
        
        Args:
            event_id: Event ID
            user_id: User ID
            required_amount: Amount needed
            
        Returns:
            Tuple of (has_sufficient, available, shortfall)
        """
        participant = mongo.participants.find_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id)
        })
        
        if not participant:
            return False, 0, required_amount
        
        available = float(participant.get("available_contribution", participant.get("balance", 0)))
        shortfall = max(0, required_amount - available)
        
        return available >= required_amount, available, shortfall
    
    @classmethod
    def get_user_contribution(cls, event_id: str, user_id: str) -> Dict[str, float]:
        """Get user's contribution details in an event."""
        participant = mongo.participants.find_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id)
        })
        
        if not participant:
            return {
                "deposited": 0,
                "spent": 0,
                "balance": 0,
                "available": 0
            }
        
        return {
            "deposited": round(participant.get("deposit_amount", 0), 2),
            "spent": round(participant.get("total_spent", 0), 2),
            "balance": round(participant.get("balance", 0), 2),
            "available": round(participant.get("available_contribution", participant.get("balance", 0)), 2)
        }
    
    @classmethod
    def revert_expense(
        cls,
        event_id: str,
        expense_id: str,
        total_amount: float,
        splits: list
    ) -> Tuple[bool, str]:
        """
        Revert an expense deduction (e.g., on cancellation).
        
        Args:
            event_id: Event ID
            expense_id: Expense ID
            total_amount: Total expense amount to revert
            splits: List of {user_id, amount} dicts
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Revert event total spent
            mongo.events.update_one(
                {"_id": ObjectId(event_id)},
                {
                    "$inc": {"total_spent": -total_amount},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            # Revert individual participant balances
            for split in splits:
                user_id = split["user_id"]
                amount = float(split["amount"])
                
                mongo.participants.update_one(
                    {
                        "event_id": ObjectId(event_id),
                        "user_id": ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id
                    },
                    {
                        "$inc": {
                            "total_spent": -amount,
                            "balance": amount,
                            "available_contribution": amount
                        },
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
            
            # Record reversal activity
            mongo.activities.insert_one({
                "type": "expense_reverted",
                "event_id": ObjectId(event_id),
                "expense_id": ObjectId(expense_id),
                "amount": total_amount,
                "description": f"Expense reverted: ${total_amount:.2f}",
                "created_at": datetime.utcnow()
            })
            
            return True, ""
            
        except Exception as e:
            return False, f"Revert failed: {str(e)}"
