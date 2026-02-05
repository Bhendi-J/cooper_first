"""
Wallet Fallback Service - Personal wallet integration.

Responsibilities:
- Handle shortfall when contribution is insufficient
- Deduct from personal wallet if permitted
- Create debt records if wallet insufficient
- Handle wallet top-ups
"""
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from bson import ObjectId

from app.extensions import db as mongo


class WalletFallbackService:
    """Service for personal wallet fallback logic."""
    
    @classmethod
    def get_wallet_balance(cls, user_id: str) -> float:
        """Get user's personal wallet balance."""
        wallet = mongo.wallets.find_one({"user_id": ObjectId(user_id)})
        if not wallet:
            # Create wallet if doesn't exist
            mongo.wallets.insert_one({
                "user_id": ObjectId(user_id),
                "balance": 0.0,
                "created_at": datetime.utcnow()
            })
            return 0.0
        return float(wallet.get("balance", 0))
    
    @classmethod
    def credit_wallet(
        cls,
        user_id: str,
        amount: float,
        source: str,
        reference_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[bool, float]:
        """
        Credit user's personal wallet.
        
        Args:
            user_id: User ID
            amount: Amount to credit
            source: Source of credit (topup, refund, etc.)
            reference_id: Reference to payment/transaction
            notes: Optional notes
            
        Returns:
            Tuple of (success, new_balance)
        """
        amount = round(float(amount), 2)
        
        # Ensure wallet exists
        wallet = mongo.wallets.find_one({"user_id": ObjectId(user_id)})
        if not wallet:
            result = mongo.wallets.insert_one({
                "user_id": ObjectId(user_id),
                "balance": amount,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            wallet_id = result.inserted_id
            new_balance = amount
        else:
            wallet_id = wallet["_id"]
            mongo.wallets.update_one(
                {"_id": wallet_id},
                {
                    "$inc": {"balance": amount},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            new_balance = float(wallet.get("balance", 0)) + amount
        
        # Record transaction
        mongo.wallet_transactions.insert_one({
            "wallet_id": wallet_id,
            "user_id": ObjectId(user_id),
            "type": "credit",
            "amount": amount,
            "source": source,
            "reference_id": reference_id,
            "notes": notes,
            "balance_after": new_balance,
            "created_at": datetime.utcnow()
        })
        
        return True, round(new_balance, 2)
    
    @classmethod
    def debit_wallet(
        cls,
        user_id: str,
        amount: float,
        purpose: str,
        reference_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[bool, Optional[str], float]:
        """
        Debit user's personal wallet.
        
        Args:
            user_id: User ID
            amount: Amount to debit
            purpose: Purpose of debit
            reference_id: Reference to expense/debt
            notes: Optional notes
            
        Returns:
            Tuple of (success, error_message, amount_debited)
        """
        amount = round(float(amount), 2)
        
        wallet = mongo.wallets.find_one({"user_id": ObjectId(user_id)})
        if not wallet:
            return False, "No wallet found", 0.0
        
        current_balance = float(wallet.get("balance", 0))
        
        if current_balance < amount:
            return False, f"Insufficient wallet balance (${current_balance:.2f})", 0.0
        
        new_balance = current_balance - amount
        
        mongo.wallets.update_one(
            {"_id": wallet["_id"]},
            {
                "$inc": {"balance": -amount},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # Record transaction
        mongo.wallet_transactions.insert_one({
            "wallet_id": wallet["_id"],
            "user_id": ObjectId(user_id),
            "type": "debit",
            "amount": amount,
            "purpose": purpose,
            "reference_id": reference_id,
            "notes": notes,
            "balance_after": new_balance,
            "created_at": datetime.utcnow()
        })
        
        return True, None, amount
    
    @classmethod
    def handle_shortfall(
        cls,
        user_id: str,
        event_id: str,
        expense_id: str,
        required_amount: float,
        available_contribution: float
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Handle shortfall when user's contribution is insufficient.
        
        Logic:
        1. Calculate shortfall
        2. Try to debit from personal wallet
        3. If wallet insufficient, create debt record
        
        Args:
            user_id: User ID
            event_id: Event ID
            expense_id: Related expense ID
            required_amount: Amount needed for expense share
            available_contribution: Amount available in contribution
            
        Returns:
            Tuple of (success, debt_info if created)
        """
        from .debt_service import DebtService
        from .notification_service import NotificationService
        
        shortfall = max(0, required_amount - available_contribution)
        
        if shortfall <= 0:
            return True, None
        
        # Try wallet debit
        wallet_balance = cls.get_wallet_balance(user_id)
        
        if wallet_balance >= shortfall:
            # Wallet covers shortfall
            success, error, _ = cls.debit_wallet(
                user_id=user_id,
                amount=shortfall,
                purpose="expense_shortfall",
                reference_id=expense_id,
                notes=f"Covered shortfall for expense in event {event_id}"
            )
            
            if success:
                # Record that wallet was used
                mongo.wallet_usage.insert_one({
                    "user_id": ObjectId(user_id),
                    "event_id": ObjectId(event_id),
                    "expense_id": ObjectId(expense_id),
                    "amount": shortfall,
                    "type": "shortfall_coverage",
                    "created_at": datetime.utcnow()
                })
                return True, None
        
        # Wallet insufficient - calculate remaining debt
        wallet_contribution = min(wallet_balance, shortfall)
        remaining_debt = shortfall - wallet_contribution
        
        # Debit what we can from wallet
        if wallet_contribution > 0:
            cls.debit_wallet(
                user_id=user_id,
                amount=wallet_contribution,
                purpose="expense_shortfall_partial",
                reference_id=expense_id
            )
        
        # Create debt record
        if remaining_debt > 0:
            debt_info = DebtService.create_debt(
                user_id=user_id,
                event_id=event_id,
                expense_id=expense_id,
                amount=remaining_debt,
                reason="Expense share exceeded available contribution and wallet balance"
            )
            
            # Notify user
            NotificationService.notify_debt_created(
                user_id=user_id,
                amount=remaining_debt,
                event_id=event_id,
                expense_id=expense_id
            )
            
            return True, debt_info
        
        return True, None
    
    @classmethod
    def process_topup(
        cls,
        user_id: str,
        amount: float,
        payment_id: str,
        apply_to_debts: bool = True
    ) -> Tuple[bool, Dict]:
        """
        Process a wallet top-up.
        
        Optionally applies excess to outstanding debts.
        
        Args:
            user_id: User ID
            amount: Top-up amount
            payment_id: Payment reference
            apply_to_debts: Whether to auto-apply to debts
            
        Returns:
            Tuple of (success, result_info)
        """
        from .debt_service import DebtService
        
        # Credit wallet
        success, new_balance = cls.credit_wallet(
            user_id=user_id,
            amount=amount,
            source="topup",
            reference_id=payment_id
        )
        
        if not success:
            return False, {"error": "Failed to credit wallet"}
        
        result = {
            "credited": amount,
            "new_balance": new_balance,
            "debts_settled": []
        }
        
        # Apply to outstanding debts if enabled
        if apply_to_debts:
            outstanding = DebtService.get_user_outstanding_debts(user_id)
            
            remaining_balance = new_balance
            for debt in outstanding:
                if remaining_balance <= 0:
                    break
                
                debt_amount = float(debt["amount_remaining"])
                settle_amount = min(remaining_balance, debt_amount)
                
                # Settle debt
                success, _ = DebtService.settle_debt(
                    debt_id=debt["_id"],
                    payment_id=payment_id,
                    amount=settle_amount
                )
                
                if success:
                    # Debit from wallet
                    cls.debit_wallet(
                        user_id=user_id,
                        amount=settle_amount,
                        purpose="debt_settlement",
                        reference_id=debt["_id"]
                    )
                    
                    remaining_balance -= settle_amount
                    result["debts_settled"].append({
                        "debt_id": debt["_id"],
                        "amount": settle_amount
                    })
            
            result["new_balance"] = remaining_balance
        
        return True, result
    
    @classmethod
    def get_wallet_transactions(
        cls,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get wallet transaction history."""
        transactions = list(mongo.wallet_transactions.find({
            "user_id": ObjectId(user_id)
        }).sort("created_at", -1).limit(limit))
        
        for t in transactions:
            t["_id"] = str(t["_id"])
            t["user_id"] = str(t["user_id"])
            t["wallet_id"] = str(t["wallet_id"])
        
        return transactions
